"""Export the approved Preview content bundle (recipes, printables, settings) by explicit UUID.
Read-only against the source DB. Never includes users, files, profiles, journals, payments, codes or env values.

Usage:  python tools/export_content_bundle.py [--out content_bundle.json]
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env")

# ---- Approved record IDs (explicit; title matching is deliberately not used) ----
APPROVED_RECIPE_IDS = [
    "a2797439-872e-488c-ac32-51e026e0333a",  # Apple Cinnamon Snack Muffins
    "af0260d1-7652-4d0a-9ec4-b9de54714f1a",  # Rainbow Veggie Wraps
    "7b765bbd-ec97-41ea-b913-a8f4b81bdf3c",  # Teen Chef Chicken Stir-Fry
    "e3f8fcfb-0eb2-4614-b63d-19bf730912e2",  # 20-Minute Sheet Pan Salmon
    "8420b592-f937-4ea7-b1c4-233e14b4a607",  # Weeknight Beef Tacos
    "502ef474-b8a0-4f5e-8188-d09af0fd0bce",  # Rainbow Fruit Kabobs
]
APPROVED_PRINTABLE_IDS = [
    "6894d221-3a53-423e-870e-a29ce6745a54",  # Kitchen Tools Coloring Page
    "924178ba-9f25-45c3-a6a8-f82530f0c1b3",  # Food Group Match Worksheet
    "73e0b3f0-a355-405e-ac12-4616b63a88ce",  # My Blank Shopping List
    "23b621c1-e853-4c17-9338-daa51e3334d7",  # Meal Costing Worksheet
    "e53427b2-294d-40ae-b147-404c677b7251",  # Weekly Family Learning Guide - Fractions in the Kitchen
]
REQUIRED_SETTINGS = ["feature_flags", "featured_recipe"]
OPTIONAL_SETTINGS = ["etsy_url"]

# Fields that must never travel (storage refs are environment-specific; analytics are Preview-only)
RECIPE_DROP = {"_id", "photo_file_id", "recipe_card_file_id"}
PRINTABLE_DROP = {"_id", "pdf_file_id", "thumbnail_file_id"}
BUNDLE_VERSION = 1


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_bundle(db) -> dict:
    recipes, printables, settings = [], [], []
    for rid in APPROVED_RECIPE_IDS:
        doc = db.recipes.find_one({"id": rid})
        if not doc: sys.exit(f"export: approved recipe {rid} not found")
        recipes.append({k: v for k, v in doc.items() if k not in RECIPE_DROP})
    for pid in APPROVED_PRINTABLE_IDS:
        doc = db.printables.find_one({"id": pid})
        if not doc: sys.exit(f"export: approved printable {pid} not found")
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
    return {
        "bundle_version": BUNDLE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": "preview",
        "recipes": recipes, "printables": printables, "settings": settings,
    }


def manifest(bundle: dict, checksum: str) -> str:
    lines = [f"# Content bundle manifest", f"exported_at: {bundle['exported_at']}", f"sha256: {checksum}", "",
             f"## Recipes ({len(bundle['recipes'])})"]
    lines += [f"- {r['id']} | {r['title']} | tier={r.get('tier')} | sample={bool(r.get('is_sample'))}" for r in bundle["recipes"]]
    lines += ["", f"## Printables ({len(bundle['printables'])})"]
    lines += [f"- {p['id']} | {p['title']} | kind={p.get('kind')} | tier={p.get('tier')}" for p in bundle["printables"]]
    lines += ["", f"## Settings ({len(bundle['settings'])})"]
    lines += [f"- {s['key']}: {json.dumps(s['value'], sort_keys=True)}" for s in bundle["settings"]]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(BACKEND / "content_bundle.json"))
    args = ap.parse_args()
    db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    bundle = build_bundle(db)
    data = json.dumps(bundle, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    checksum = sha256(data)
    out = Path(args.out); out.write_bytes(data)
    Path(str(out).replace(".json", ".manifest.md")).write_text(manifest(bundle, checksum))
    print(f"wrote {out} ({len(data)} bytes) sha256={checksum}")
    print(f"recipes={len(bundle['recipes'])} printables={len(bundle['printables'])} settings={len(bundle['settings'])}")


if __name__ == "__main__":
    main()
