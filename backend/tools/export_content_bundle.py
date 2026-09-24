"""Export the approved Preview content bundle (recipes, printables, settings, checksummed assets) by explicit UUID.
Read-only against the source DB. Never includes users, files metadata, profiles, journals, payments, codes or env values.
Assets (recipe photos / printable PDFs) are copied into a sibling `<bundle>_assets/` directory and referenced by
`asset:<sha256>` markers; the bundle never carries Preview file IDs, storage paths or hostnames.

Usage:  python tools/export_content_bundle.py [--out content_bundle.json]
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

# ---- Approved record IDs (explicit; title matching is deliberately not used) ----
APPROVED_RECIPE_IDS = [
    "a2797439-872e-488c-ac32-51e026e0333a",  # Apple Cinnamon Snack Muffins
    "af0260d1-7652-4d0a-9ec4-b9de54714f1a",  # Rainbow Veggie Wraps
    "7b765bbd-ec97-41ea-b913-a8f4b81bdf3c",  # Teen Chef Chicken Stir-Fry
    "e3f8fcfb-0eb2-4614-b63d-19bf730912e2",  # 20-Minute Sheet Pan Salmon
    "8420b592-f937-4ea7-b1c4-233e14b4a607",  # Weeknight Beef Tacos
    "502ef474-b8a0-4f5e-8188-d09af0fd0bce",  # Rainbow Fruit Kabobs
    "aba6b0a7-e6a3-4ce7-a017-bd71fad6a68c",  # Mini Rainbow Pizza Bites
    "b22919be-b09d-4e79-b73c-d6484e3ae5d9",  # Chocolate Chip Cookie Shop Cookies
    "da3235b8-771b-4a74-9289-5372d9eed7f8",  # Kid-Friendly Walking Tacos
    "593b7e51-26b4-4254-89e3-0a8fdc14a239",  # Dunkable Grilled Cheese & Tomato Soup
    "1bdb483c-986c-4dbc-bfe3-021b29d48e0d",  # Ultimate Smash Burgers (external photo URL)
    # "a3f29d4d-16ce-4273-8da7-0c26db31e91a",  Rainbow Fruit Kabobs (Copy) — excluded
]
APPROVED_PRINTABLE_IDS = [
    "6894d221-3a53-423e-870e-a29ce6745a54",  # Food Match and Color (branded PDF)
    "924178ba-9f25-45c3-a6a8-f82530f0c1b3",  # Food Group Match (branded PDF)
    # Hidden until branded replacements are ready — intentionally excluded from the bundle:
    # "73e0b3f0-a355-405e-ac12-4616b63a88ce",  My Blank Shopping List
    # "23b621c1-e853-4c17-9338-daa51e3334d7",  Meal Costing Worksheet
    # "e53427b2-294d-40ae-b147-404c677b7251",  Weekly Family Learning Guide - Fractions in the Kitchen
]
REQUIRED_SETTINGS = ["feature_flags", "featured_recipe"]
OPTIONAL_SETTINGS = ["etsy_url"]

# Fields that must never travel (storage refs are environment-specific; analytics are Preview-only)
RECIPE_DROP = {"_id", "photo_file_id", "recipe_card_file_id"}
PRINTABLE_DROP = {"_id", "pdf_file_id", "thumbnail_file_id", "is_hidden"}
BUNDLE_VERSION = 2
ASSET_EXT = {"image/jpeg": "jpg", "application/pdf": "pdf"}
ASSET_PURPOSE = {"recipes": ("photo_file_id", "recipe_photo", "image/jpeg"),
                 "printables": ("pdf_file_id", "printable_pdf", "application/pdf")}
FORBIDDEN_TEXT = ("emergentagent.com", "/api/files/", "localhost", "127.0.0.1", "mongodb://", "storage_path")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assets_dir_for(bundle_path: Path) -> Path:
    return bundle_path.with_name(bundle_path.stem + "_assets")


def _pdf_pages(data: bytes) -> int:
    from pypdf import PdfReader
    try: return len(PdfReader(io.BytesIO(data)).pages)
    except Exception: return 0


def _fetch_asset(db, get_object, coll: str, doc: dict) -> tuple[dict, bytes]:
    """Read one owned asset from Preview storage and build its manifest entry (no Preview identifiers)."""
    ref_field, purpose, mime = ASSET_PURPOSE[coll]
    rec = db.files.find_one({"id": doc[ref_field], "is_deleted": False})
    if not rec: sys.exit(f"export: {coll} {doc['id']} references missing file {doc[ref_field]}")
    if rec.get("purpose") != purpose: sys.exit(f"export: file {rec['id']} has purpose {rec.get('purpose')!r}, expected {purpose!r}")
    if rec.get("content_type") != mime: sys.exit(f"export: file {rec['id']} has MIME {rec.get('content_type')!r}, expected {mime!r}")
    data, _ = get_object(rec["storage_path"])
    if len(data) != rec.get("size"): sys.exit(f"export: file {rec['id']} size mismatch ({len(data)} != {rec.get('size')})")
    if mime == "image/jpeg" and not data.startswith(b"\xff\xd8\xff"): sys.exit(f"export: file {rec['id']} is not a JPEG")
    if mime == "application/pdf" and _pdf_pages(data) < 1: sys.exit(f"export: file {rec['id']} is not a valid PDF")
    entry = {"collection": coll, "owner_id": doc["id"], "purpose": purpose,
             "filename": f"{purpose}__{doc['id']}.{ASSET_EXT[mime]}", "content_type": mime,
             "size": len(data), "sha256": sha256(data)}
    return entry, data


def build_bundle(db, get_object=None) -> tuple[dict, dict[str, bytes]]:
    if get_object is None:
        from storage import get_object  # noqa: WPS433
    recipes, printables, settings, assets, blobs = [], [], [], [], {}
    for rid in APPROVED_RECIPE_IDS:
        doc = db.recipes.find_one({"id": rid})
        if not doc: sys.exit(f"export: approved recipe {rid} not found")
        if doc.get("photo_file_id"):
            entry, data = _fetch_asset(db, get_object, "recipes", doc)
            assets.append(entry); blobs[entry["filename"]] = data
            doc["photo_url"] = f"asset:{entry['sha256']}"
        elif doc.get("photo_url") and not re.match(r"^https://", doc["photo_url"]):
            sys.exit(f"export: recipe {rid} photo_url is neither an owned file nor an https URL")
        recipes.append({k: v for k, v in doc.items() if k not in RECIPE_DROP})
    for pid in APPROVED_PRINTABLE_IDS:
        doc = db.printables.find_one({"id": pid})
        if not doc: sys.exit(f"export: approved printable {pid} not found")
        if doc.get("is_hidden"): sys.exit(f"export: printable {pid} is hidden from members; unhide it or remove it from the approved list")
        if not doc.get("pdf_file_id"): sys.exit(f"export: printable {pid} has no uploaded PDF")
        entry, data = _fetch_asset(db, get_object, "printables", doc)
        assets.append(entry); blobs[entry["filename"]] = data
        doc = {k: v for k, v in doc.items() if k not in PRINTABLE_DROP}
        doc["download_count"] = 0
        printables.append(doc)
    for key in REQUIRED_SETTINGS + OPTIONAL_SETTINGS:
        doc = db.settings.find_one({"key": key}, {"_id": 0})
        if not doc:
            if key in REQUIRED_SETTINGS: sys.exit(f"export: required setting {key!r} missing")
            continue
        settings.append({"key": key, "value": doc.get("value")})
    feat = next((s for s in settings if s["key"] == "featured_recipe"), None)
    if feat and feat["value"].get("recipe_id") and feat["value"]["recipe_id"] not in APPROVED_RECIPE_IDS:
        sys.exit("export: featured_recipe points at a recipe that is not in the approved list")
    if len({a["sha256"] for a in assets}) != len(assets): sys.exit("export: duplicate asset content detected")
    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": "preview",
        "recipes": recipes, "printables": printables, "settings": settings, "assets": assets,
    }
    return bundle, blobs


def serialize(bundle: dict) -> bytes:
    return json.dumps(bundle, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


def manifest(bundle: dict, checksum: str) -> str:
    lines = [f"# Content bundle manifest", f"bundle_version: {bundle['bundle_version']}",
             f"exported_at: {bundle['exported_at']}", f"sha256: {checksum}", "",
             f"## Recipes ({len(bundle['recipes'])})"]
    lines += [f"- {r['id']} | {r['title']} | tier={r.get('tier')} | sample={bool(r.get('is_sample'))} | photo={r.get('photo_url') or '-'}"
              for r in bundle["recipes"]]
    lines += ["", f"## Printables ({len(bundle['printables'])})"]
    lines += [f"- {p['id']} | {p['title']} | kind={p.get('kind')} | tier={p.get('tier')}" for p in bundle["printables"]]
    lines += ["", f"## Settings ({len(bundle['settings'])})"]
    lines += [f"- {s['key']}: {json.dumps(s['value'], sort_keys=True)}" for s in bundle["settings"]]
    lines += ["", f"## Assets ({len(bundle['assets'])})"]
    lines += [f"- {a['collection']} | {a['owner_id']} | {a['purpose']} | {a['filename']} | {a['content_type']} | {a['size']} B | sha256={a['sha256']}"
              for a in bundle["assets"]]
    return "\n".join(lines) + "\n"


def write_assets(assets_dir: Path, bundle: dict, blobs: dict[str, bytes]) -> None:
    """Write the asset directory so that it contains exactly the manifested files, then re-verify from disk."""
    assets_dir.mkdir(exist_ok=True)
    wanted = {a["filename"] for a in bundle["assets"]}
    for p in assets_dir.iterdir():
        if p.name not in wanted: p.unlink()
    for a in bundle["assets"]:
        (assets_dir / a["filename"]).write_bytes(blobs[a["filename"]])
    on_disk = {p.name for p in assets_dir.iterdir()}
    if on_disk != wanted: sys.exit(f"export: asset dir mismatch {sorted(on_disk ^ wanted)}")
    for a in bundle["assets"]:
        data = (assets_dir / a["filename"]).read_bytes()
        if len(data) != a["size"] or sha256(data) != a["sha256"]: sys.exit(f"export: asset {a['filename']} failed post-write verification")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BACKEND / "content_bundle.json"))
    args = ap.parse_args()
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    bundle, blobs = build_bundle(db)
    data = serialize(bundle)
    checksum = sha256(data)
    text = data.decode("utf-8") + manifest(bundle, checksum)
    public_host = re.sub(r"^https?://", "", os.environ.get("APP_PUBLIC_URL", "")).strip("/")
    for bad in FORBIDDEN_TEXT + ((public_host,) if public_host else ()):
        if bad in text: sys.exit(f"export: bundle/manifest contains forbidden text {bad!r}")
    out = Path(args.out)
    write_assets(assets_dir_for(out), bundle, blobs)
    out.write_bytes(data)
    Path(str(out).replace(".json", ".manifest.md")).write_text(manifest(bundle, checksum))
    print(f"wrote {out} ({len(data)} bytes) sha256={checksum}")
    print(f"recipes={len(bundle['recipes'])} printables={len(bundle['printables'])} settings={len(bundle['settings'])} assets={len(bundle['assets'])}")
    for a in bundle["assets"]: print(f"  asset {a['filename']} {a['size']} B sha256={a['sha256']}")


if __name__ == "__main__":
    main()
