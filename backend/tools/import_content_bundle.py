"""Import the approved content bundle into a fresh production database. Dry-run by default.

Writes happen only with --apply AND APP_ENV=production, and never into a DB whose name looks like
preview/test/dev. Imports recipes, printables and the whitelisted settings only — nothing else.

Usage:  python tools/import_content_bundle.py [--bundle content_bundle.json] [--apply]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND = Path(__file__).resolve().parents[1]
ALLOWED_COLLECTIONS = ("recipes", "printables", "settings")
ALLOWED_SETTING_KEYS = {"feature_flags", "featured_recipe", "etsy_url"}
FORBIDDEN_FIELDS = {"_id", "photo_file_id", "recipe_card_file_id", "pdf_file_id", "thumbnail_file_id", "password_hash", "email"}
UNSAFE_DB = re.compile(r"(preview|test|dev|develop|development|staging|local|sandbox)", re.I)
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class Refuse(SystemExit):
    def __init__(self, msg): super().__init__(f"import: REFUSED — {msg}")


def load_bundle(path: Path) -> tuple[dict, str]:
    data = path.read_bytes()
    bundle = json.loads(data)
    if bundle.get("bundle_version") != 1: raise Refuse("unsupported bundle_version")
    for k in ("recipes", "printables", "settings"):
        if not isinstance(bundle.get(k), list): raise Refuse(f"bundle missing list {k!r}")
    extra = set(bundle) - {"bundle_version", "exported_at", "source", "recipes", "printables", "settings"}
    if extra: raise Refuse(f"bundle contains unexpected top-level keys {sorted(extra)}")
    for coll in ("recipes", "printables"):
        for doc in bundle[coll]:
            if not UUID.match(str(doc.get("id", ""))): raise Refuse(f"{coll} document without UUID id")
            bad = FORBIDDEN_FIELDS & set(doc)
            if bad: raise Refuse(f"{coll} {doc['id']} carries forbidden fields {sorted(bad)}")
            if not doc.get("title"): raise Refuse(f"{coll} {doc['id']} has no title")
    for s in bundle["settings"]:
        if s.get("key") not in ALLOWED_SETTING_KEYS: raise Refuse(f"setting {s.get('key')!r} is not allowed")
    return bundle, hashlib.sha256(data).hexdigest()


def plan(db, bundle: dict) -> list[str]:
    """Idempotent upsert plan. Aborts on conflicting existing content."""
    actions = []
    for coll in ("recipes", "printables"):
        for doc in bundle[coll]:
            existing = db[coll].find_one({"id": doc["id"]}, {"_id": 0})
            if existing is None:
                actions.append(f"INSERT {coll} {doc['id']} | {doc['title']}")
            elif existing == doc:
                actions.append(f"SKIP   {coll} {doc['id']} | {doc['title']} (identical)")
            else:
                diff = sorted(k for k in set(existing) | set(doc) if existing.get(k) != doc.get(k))
                raise Refuse(f"{coll} {doc['id']} already exists with different content (fields: {diff}). "
                             f"Resolve manually; this tool never overwrites.")
        # Same title under a different UUID is a duplicate-content conflict
        for doc in bundle[coll]:
            clash = db[coll].find_one({"title": doc["title"], "id": {"$ne": doc["id"]}}, {"id": 1})
            if clash: raise Refuse(f"{coll} title {doc['title']!r} already exists under a different id {clash['id']}")
    for s in bundle["settings"]:
        existing = db.settings.find_one({"key": s["key"]}, {"_id": 0})
        if existing is None: actions.append(f"INSERT settings {s['key']} = {json.dumps(s['value'], sort_keys=True)}")
        elif existing.get("value") == s["value"]: actions.append(f"SKIP   settings {s['key']} (identical)")
        else: raise Refuse(f"setting {s['key']!r} already exists with a different value; this tool never overwrites")
    return actions


def apply(db, bundle: dict) -> None:
    for coll in ("recipes", "printables"):
        for doc in bundle[coll]:
            db[coll].update_one({"id": doc["id"]}, {"$setOnInsert": doc}, upsert=True)
    for s in bundle["settings"]:
        db.settings.update_one({"key": s["key"]}, {"$setOnInsert": {"key": s["key"], "value": s["value"]}}, upsert=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=str(BACKEND / "content_bundle.json"))
    ap.add_argument("--apply", action="store_true", help="perform writes (also requires APP_ENV=production)")
    args = ap.parse_args()
    load_dotenv(BACKEND / ".env")

    db_name = os.environ.get("DB_NAME", "")
    if not db_name or not os.environ.get("MONGO_URL"): raise Refuse("MONGO_URL/DB_NAME not configured")
    if UNSAFE_DB.search(db_name): raise Refuse(f"DB_NAME {db_name!r} looks like a preview/test/dev database")

    bundle, checksum = load_bundle(Path(args.bundle))
    db = MongoClient(os.environ["MONGO_URL"])[db_name]
    actions = plan(db, bundle)

    print(f"target DB_NAME : {db_name}")
    print(f"bundle         : {args.bundle} sha256={checksum}")
    print(f"recipes={len(bundle['recipes'])} printables={len(bundle['printables'])} settings={len(bundle['settings'])}")
    for a in actions: print("  " + a)

    if not args.apply:
        print("DRY RUN — no changes made. Re-run with --apply and APP_ENV=production to write.")
        return
    if os.environ.get("APP_ENV", "").lower() != "production":
        raise Refuse("--apply requires APP_ENV=production")
    apply(db, bundle)
    print(f"APPLIED to {db_name}: {sum(a.startswith('INSERT') for a in actions)} inserted, "
          f"{sum(a.startswith('SKIP') for a in actions)} skipped")


if __name__ == "__main__":
    main()
