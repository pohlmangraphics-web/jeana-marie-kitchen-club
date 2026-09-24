"""Import the approved content bundle (+ checksummed assets) into a fresh production database. Dry-run by default.

Writes happen only with --apply AND APP_ENV=production, never into a DB whose name looks like preview/test/dev,
and only after every manifest, hash, MIME, ownership, conflict, database, environment and URL check has passed.
Assets are uploaded into the target environment's storage under NEW file UUIDs; Preview file IDs/paths never travel.

Usage:  python tools/import_content_bundle.py [--bundle content_bundle.json] [--apply]
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import storage  # noqa: E402

ALLOWED_COLLECTIONS = ("recipes", "printables", "settings")
ALLOWED_SETTING_KEYS = {"feature_flags", "featured_recipe", "etsy_url"}
FORBIDDEN_FIELDS = {"_id", "photo_file_id", "recipe_card_file_id", "pdf_file_id", "thumbnail_file_id", "password_hash", "email"}
TOP_LEVEL_KEYS = {"bundle_version", "exported_at", "source", "recipes", "printables", "settings", "assets"}
ASSET_KEYS = {"collection", "owner_id", "purpose", "filename", "content_type", "size", "sha256"}
ASSET_RULES = {  # purpose -> (owning collection, reference field, MIME, extension, magic bytes)
    "recipe_photo": ("recipes", "photo_file_id", "image/jpeg", "jpg", b"\xff\xd8\xff"),
    "printable_pdf": ("printables", "pdf_file_id", "application/pdf", "pdf", b"%PDF-"),
}
UNSAFE_DB = re.compile(r"(preview|test|dev|develop|development|staging|local|sandbox)", re.I)
UNSAFE_HOST = re.compile(r"(preview|test|dev|staging|sandbox|local|127\.0\.0\.1|0\.0\.0\.0)", re.I)
FORBIDDEN_TEXT = ("emergentagent.com", "/api/files/", "localhost", "127.0.0.1", "mongodb://", "storage_path")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,120}\.(jpg|pdf)$")
SHA = re.compile(r"^[0-9a-f]{64}$")
MARKER = re.compile(r"^asset:([0-9a-f]{64})$")
IMPORTER_ID = "content_bundle_import"


class Refuse(SystemExit):
    def __init__(self, msg): super().__init__(f"import: REFUSED — {msg}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assets_dir_for(bundle_path: Path) -> Path:
    return bundle_path.with_name(bundle_path.stem + "_assets")


def _pdf_pages(data: bytes) -> int:
    from pypdf import PdfReader
    try: return len(PdfReader(io.BytesIO(data)).pages)
    except Exception: return 0


# ---------------------------------------------------------------- validation (no I/O beyond reading the bundle)
def load_bundle(path: Path) -> tuple[dict, str]:
    data = path.read_bytes()
    bundle = json.loads(data)
    if bundle.get("bundle_version") != 2: raise Refuse("unsupported bundle_version (expected 2)")
    for k in ("recipes", "printables", "settings", "assets"):
        if not isinstance(bundle.get(k), list): raise Refuse(f"bundle missing list {k!r}")
    extra = set(bundle) - TOP_LEVEL_KEYS
    if extra: raise Refuse(f"bundle contains unexpected top-level keys {sorted(extra)}")
    ids = {"recipes": set(), "printables": set()}
    for coll in ("recipes", "printables"):
        for doc in bundle[coll]:
            if not UUID.match(str(doc.get("id", ""))): raise Refuse(f"{coll} document without UUID id")
            if doc["id"] in ids[coll]: raise Refuse(f"{coll} {doc['id']} appears twice")
            ids[coll].add(doc["id"])
            bad = FORBIDDEN_FIELDS & set(doc)
            if bad: raise Refuse(f"{coll} {doc['id']} carries forbidden fields {sorted(bad)}")
            if not doc.get("title"): raise Refuse(f"{coll} {doc['id']} has no title")
    for s in bundle["settings"]:
        if s.get("key") not in ALLOWED_SETTING_KEYS: raise Refuse(f"setting {s.get('key')!r} is not allowed")
    _validate_assets(bundle, ids)
    text = data.decode("utf-8")
    for bad in FORBIDDEN_TEXT:
        if bad in text: raise Refuse(f"bundle contains forbidden text {bad!r} (Preview identifiers must not travel)")
    return bundle, sha256(data)


def _validate_assets(bundle: dict, ids: dict) -> None:
    seen_owner, seen_name, seen_sha = set(), set(), set()
    by_sha = {}
    for a in bundle["assets"]:
        if set(a) != ASSET_KEYS: raise Refuse(f"asset entry keys must be exactly {sorted(ASSET_KEYS)}")
        rule = ASSET_RULES.get(a["purpose"])
        if not rule: raise Refuse(f"asset purpose {a['purpose']!r} is not allowed")
        coll, _field, mime, ext, _magic = rule
        if a["collection"] != coll: raise Refuse(f"asset purpose {a['purpose']} must belong to {coll}, got {a['collection']}")
        if not UUID.match(str(a["owner_id"])) or a["owner_id"] not in ids[coll]:
            raise Refuse(f"asset owner {a['owner_id']} is not a {coll} document in this bundle")
        fn = a["filename"]
        if not isinstance(fn, str) or not SAFE_FILENAME.match(fn) or "/" in fn or "\\" in fn or ".." in fn or Path(fn).is_absolute() or Path(fn).name != fn:
            raise Refuse(f"unsafe asset filename {fn!r}")
        if not fn.endswith("." + ext) or a["content_type"] != mime: raise Refuse(f"asset {fn} MIME/extension mismatch for purpose {a['purpose']}")
        if not isinstance(a["size"], int) or isinstance(a["size"], bool) or a["size"] <= 0: raise Refuse(f"asset {fn} has invalid size")
        if not isinstance(a["sha256"], str) or not SHA.match(a["sha256"]): raise Refuse(f"asset {fn} has invalid sha256")
        key = (coll, a["owner_id"], a["purpose"])
        if key in seen_owner: raise Refuse(f"duplicate asset for {coll} {a['owner_id']} purpose {a['purpose']}")
        if fn in seen_name: raise Refuse(f"duplicate asset filename {fn}")
        if a["sha256"] in seen_sha: raise Refuse(f"duplicate asset content sha256={a['sha256']}")
        seen_owner.add(key); seen_name.add(fn); seen_sha.add(a["sha256"]); by_sha[a["sha256"]] = a
    # Every recipe photo marker must point at an asset owned by that recipe; every asset must be referenced
    referenced = set()
    for r in bundle["recipes"]:
        url = r.get("photo_url")
        if not url: continue
        m = MARKER.match(url)
        if m:
            a = by_sha.get(m.group(1))
            if not a or a["owner_id"] != r["id"] or a["purpose"] != "recipe_photo":
                raise Refuse(f"recipe {r['id']} photo marker does not match an asset owned by it")
            referenced.add(a["filename"])
        elif not (url.startswith("https://") and not UNSAFE_HOST.search(urlparse(url).hostname or "")):
            raise Refuse(f"recipe {r['id']} photo_url must be an asset marker or a safe https URL")
    for p in bundle["printables"]:
        owned = [a for a in bundle["assets"] if a["collection"] == "printables" and a["owner_id"] == p["id"]]
        if len(owned) != 1: raise Refuse(f"printable {p['id']} must own exactly one printable_pdf asset")
        referenced.add(owned[0]["filename"])
    unreferenced = seen_name - referenced
    if unreferenced: raise Refuse(f"unmanifested/unreferenced assets {sorted(unreferenced)}")


def verify_assets(assets_dir: Path, bundle: dict) -> dict[str, bytes]:
    """Directory must contain exactly the manifested files, each matching size, SHA-256 and MIME signature."""
    if not assets_dir.is_dir(): raise Refuse(f"assets directory {assets_dir} missing")
    on_disk = {p.name for p in assets_dir.iterdir()}
    wanted = {a["filename"] for a in bundle["assets"]}
    if on_disk - wanted: raise Refuse(f"extra unmanifested files in assets dir {sorted(on_disk - wanted)}")
    if wanted - on_disk: raise Refuse(f"missing asset files {sorted(wanted - on_disk)}")
    blobs = {}
    for a in bundle["assets"]:
        p = assets_dir / a["filename"]
        if not p.is_file() or p.is_symlink() or p.resolve().parent != assets_dir.resolve(): raise Refuse(f"asset {a['filename']} is not a regular file inside the assets dir")
        data = p.read_bytes()
        if len(data) != a["size"]: raise Refuse(f"asset {a['filename']} size {len(data)} != manifest {a['size']}")
        if sha256(data) != a["sha256"]: raise Refuse(f"asset {a['filename']} SHA-256 does not match manifest")
        magic = ASSET_RULES[a["purpose"]][4]
        if not data.startswith(magic): raise Refuse(f"asset {a['filename']} content does not match MIME {a['content_type']}")
        if a["purpose"] == "printable_pdf" and _pdf_pages(data) < 1: raise Refuse(f"asset {a['filename']} is not a readable PDF")
        blobs[a["filename"]] = data
    return blobs


def check_public_url(raw: str | None) -> str:
    if not raw: raise Refuse("APP_PUBLIC_URL not configured")
    u = urlparse(raw.strip())
    host = u.hostname or ""
    if u.scheme != "https" or not host or u.path not in ("", "/") or u.query or u.fragment:
        raise Refuse(f"APP_PUBLIC_URL {raw!r} must be a bare https origin")
    if UNSAFE_HOST.search(host): raise Refuse(f"APP_PUBLIC_URL host {host!r} looks like a preview/test/dev address")
    return f"https://{u.netloc}"


# ---------------------------------------------------------------- planning (read-only against target)
def _asset_map(bundle: dict) -> dict[tuple[str, str], dict]:
    return {(a["collection"], a["owner_id"]): a for a in bundle["assets"]}


def _existing_file(db, a: dict):
    """Idempotency lookup: owner + purpose (+ sha). Same owner/purpose with a different hash is a conflict."""
    q = {"owner_collection": a["collection"], "owner_id": a["owner_id"], "purpose": a["purpose"], "is_deleted": False}
    rec = db.files.find_one(q, {"_id": 0})
    if rec and rec.get("sha256") != a["sha256"]:
        raise Refuse(f"target already has a {a['purpose']} for {a['collection']} {a['owner_id']} with a different SHA-256; this tool never overwrites")
    return rec


def _final_doc(doc: dict, coll: str, a: dict | None, file_id: str | None, public_url: str) -> dict:
    out = dict(doc)
    if a is None: return out
    field = ASSET_RULES[a["purpose"]][1]
    out[field] = file_id
    if coll == "recipes": out["photo_url"] = f"{public_url}/api/files/{file_id}"
    return out


def plan(db, bundle: dict, public_url: str) -> tuple[list[str], dict]:
    """Idempotent plan. Aborts on any conflicting existing content or asset. Returns (actions, resolved-file-ids)."""
    actions, resolved = [], {}
    amap = _asset_map(bundle)
    for a in bundle["assets"]:
        rec = _existing_file(db, a)
        resolved[(a["collection"], a["owner_id"])] = rec["id"] if rec else None
        actions.append(f"{'SKIP   asset' if rec else 'UPLOAD asset'} {a['purpose']} {a['filename']} ({a['size']} B)" + (" (already present)" if rec else ""))
    for coll in ("recipes", "printables"):
        for doc in bundle[coll]:
            a = amap.get((coll, doc["id"]))
            fid = resolved.get((coll, doc["id"]))
            existing = db[coll].find_one({"id": doc["id"]}, {"_id": 0})
            if existing is None:
                actions.append(f"INSERT {coll} {doc['id']} | {doc['title']}")
            elif a is not None and fid is None:
                raise Refuse(f"{coll} {doc['id']} already exists but its {a['purpose']} asset is missing from the target; resolve manually")
            elif existing == _final_doc(doc, coll, a, fid, public_url):
                actions.append(f"SKIP   {coll} {doc['id']} | {doc['title']} (identical)")
            else:
                final = _final_doc(doc, coll, a, fid, public_url)
                diff = sorted(k for k in set(existing) | set(final) if existing.get(k) != final.get(k))
                raise Refuse(f"{coll} {doc['id']} already exists with different content (fields: {diff}). "
                             f"Resolve manually; this tool never overwrites.")
        for doc in bundle[coll]:
            clash = db[coll].find_one({"title": doc["title"], "id": {"$ne": doc["id"]}}, {"id": 1})
            if clash: raise Refuse(f"{coll} title {doc['title']!r} already exists under a different id {clash['id']}")
    for s in bundle["settings"]:
        existing = db.settings.find_one({"key": s["key"]}, {"_id": 0})
        if existing is None: actions.append(f"INSERT settings {s['key']} = {json.dumps(s['value'], sort_keys=True)}")
        elif existing.get("value") == s["value"]: actions.append(f"SKIP   settings {s['key']} (identical)")
        else: raise Refuse(f"setting {s['key']!r} already exists with a different value; this tool never overwrites")
    return actions, resolved


# ---------------------------------------------------------------- apply (writes)
def _upload_asset(db, a: dict, data: bytes, log: list[str]) -> str:
    """Upload one asset under a NEW file UUID and create its files record. Cleans up its own artefacts on failure."""
    file_id = str(uuid.uuid4())
    ext = ASSET_RULES[a["purpose"]][3]
    app_name = os.environ.get("APP_NAME") or storage.APP_NAME
    path = f"{app_name}/{a['purpose']}/{IMPORTER_ID}/{file_id}.{ext}"
    uploaded = inserted = False
    try:
        result = storage.put_object(path, data, a["content_type"]); uploaded = True
        back, _ = storage.get_object(result["path"])
        if sha256(back) != a["sha256"]: raise RuntimeError("uploaded object read-back hash mismatch")
        db.files.insert_one({
            "id": file_id, "storage_path": result["path"], "purpose": a["purpose"],
            "original_filename": a["filename"], "safe_filename": a["filename"], "content_type": a["content_type"],
            "size": len(data), "sha256": a["sha256"], "owner_collection": a["collection"], "owner_id": a["owner_id"],
            "uploaded_by": IMPORTER_ID, "is_deleted": False, "created_at": datetime.now(timezone.utc).isoformat(),
        }); inserted = True
        return file_id
    except Exception as e:  # remove only what this call created; never existing target data
        if inserted: db.files.delete_one({"id": file_id, "uploaded_by": IMPORTER_ID})
        if uploaded:
            removed = storage.delete_object(path)
            log.append(f"cleanup: object {path} {'removed' if removed else 'could NOT be removed (storage has no delete) — orphan, safe to ignore'}")
        raise Refuse(f"asset {a['filename']} failed during upload/record ({e}); partial artefacts cleaned up, rerun to resume")


def apply(db, bundle: dict, blobs: dict[str, bytes], resolved: dict, public_url: str, log: list[str]) -> dict:
    amap = _asset_map(bundle)
    counts = {"uploaded": 0, "inserted": 0, "skipped": 0}
    for coll in ("recipes", "printables"):
        for doc in bundle[coll]:
            a = amap.get((coll, doc["id"]))
            fid = resolved.get((coll, doc["id"]))
            if a is not None and fid is None:
                fid = _upload_asset(db, a, blobs[a["filename"]], log); counts["uploaded"] += 1
                resolved[(coll, doc["id"])] = fid
            final = _final_doc(doc, coll, a, fid, public_url)
            res = db[coll].update_one({"id": doc["id"]}, {"$setOnInsert": final}, upsert=True)
            counts["inserted" if res.upserted_id is not None else "skipped"] += 1
    for s in bundle["settings"]:
        res = db.settings.update_one({"key": s["key"]}, {"$setOnInsert": {"key": s["key"], "value": s["value"]}}, upsert=True)
        counts["inserted" if res.upserted_id is not None else "skipped"] += 1
    return counts


def verify_target(db, bundle: dict, public_url: str) -> list[str]:
    """Post-import checks: no markers, no Preview URLs, every file ref backed by a record + object with the approved hash."""
    report, amap = [], _asset_map(bundle)
    for coll in ("recipes", "printables"):
        for doc in bundle[coll]:
            tgt = db[coll].find_one({"id": doc["id"]}, {"_id": 0})
            if tgt is None: raise Refuse(f"verify: {coll} {doc['id']} missing after import")
            txt = json.dumps(tgt, default=str)
            if "asset:" in txt: raise Refuse(f"verify: {coll} {doc['id']} still carries an asset marker")
            for bad in ("emergentagent.com", "localhost", "127.0.0.1"):
                if bad in txt: raise Refuse(f"verify: {coll} {doc['id']} contains forbidden text {bad!r}")
            for m in re.finditer(r"https?://[^\s\"']+/api/files/", txt):
                if not m.group(0).startswith(public_url + "/"): raise Refuse(f"verify: {coll} {doc['id']} has a file URL outside APP_PUBLIC_URL")
            a = amap.get((coll, doc["id"]))
            if a is None: continue
            fid = tgt.get(ASSET_RULES[a["purpose"]][1])
            rec = db.files.find_one({"id": fid, "is_deleted": False}, {"_id": 0}) if fid else None
            if not rec: raise Refuse(f"verify: {coll} {doc['id']} file {fid} has no files record")
            data, _ = storage.get_object(rec["storage_path"])
            if sha256(data) != a["sha256"] or len(data) != a["size"]: raise Refuse(f"verify: {coll} {doc['id']} stored object hash/size mismatch")
            report.append(f"OK {coll} {doc['id']} -> file {fid} sha256={a['sha256'][:12]}… ({len(data)} B)")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=str(BACKEND / "content_bundle.json"))
    ap.add_argument("--apply", action="store_true", help="perform writes (also requires APP_ENV=production)")
    args = ap.parse_args()
    load_dotenv(BACKEND / ".env")

    db_name = os.environ.get("DB_NAME", "")
    if not db_name or not os.environ.get("MONGO_URL"): raise Refuse("MONGO_URL/DB_NAME not configured")
    if UNSAFE_DB.search(db_name): raise Refuse(f"DB_NAME {db_name!r} looks like a preview/test/dev database")
    if args.apply and os.environ.get("APP_ENV", "").lower() != "production":
        raise Refuse("--apply requires APP_ENV=production")

    bundle_path = Path(args.bundle)
    bundle, checksum = load_bundle(bundle_path)
    blobs = verify_assets(assets_dir_for(bundle_path), bundle)
    public_url = check_public_url(os.environ.get("APP_PUBLIC_URL"))
    db = MongoClient(os.environ["MONGO_URL"])[db_name]
    actions, resolved = plan(db, bundle, public_url)

    print(f"target DB_NAME : {db_name}")
    print(f"public URL     : {public_url}")
    print(f"bundle         : {args.bundle} sha256={checksum}")
    print(f"recipes={len(bundle['recipes'])} printables={len(bundle['printables'])} settings={len(bundle['settings'])} assets={len(bundle['assets'])}")
    for a in actions: print("  " + a)

    if not args.apply:
        print("DRY RUN — no changes made. Re-run with --apply and APP_ENV=production to write.")
        return
    log: list[str] = []
    try:
        counts = apply(db, bundle, blobs, resolved, public_url, log)
    finally:
        for line in log: print("  " + line)
    for line in verify_target(db, bundle, public_url): print("  " + line)
    assets_skipped = sum(a.startswith("SKIP   asset") for a in actions)
    print(f"APPLIED to {db_name}: {counts['uploaded']} assets uploaded, {assets_skipped} assets skipped, "
          f"{counts['inserted']} inserted, {counts['skipped']} skipped")


if __name__ == "__main__":
    main()
