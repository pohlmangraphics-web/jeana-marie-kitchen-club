"""Migration tooling tests. Uses a scratch Mongo DB that is created and dropped here; never touches Preview/Live data."""
import io
import json
import os
import sys
import uuid
import contextlib
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env")
sys.path.insert(0, str(BACKEND / "tools"))
import import_content_bundle as imp  # noqa: E402
import export_content_bundle as exp  # noqa: E402

BUNDLE = BACKEND / "content_bundle.json"
SCRATCH = f"kitchen_club_prod_scratch_{uuid.uuid4().hex[:6]}"  # must NOT match the unsafe-name pattern


@pytest.fixture
def scratch_db():
    c = MongoClient(os.environ["MONGO_URL"]); db = c[SCRATCH]
    yield db
    c.drop_database(SCRATCH)


def _run(monkeypatch, db_name, argv, app_env=None):
    monkeypatch.setenv("DB_NAME", db_name)
    if app_env is None: monkeypatch.delenv("APP_ENV", raising=False)
    else: monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setattr(sys, "argv", ["import_content_bundle.py"] + argv)
    monkeypatch.setattr(imp, "load_dotenv", lambda *_a, **_k: None)  # env comes from the test, not .env
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        imp.main()
    return out.getvalue()


def test_bundle_shape_and_exclusions():
    bundle, checksum = imp.load_bundle(BUNDLE)
    assert len(bundle["recipes"]) == 6 and len(bundle["printables"]) == 5
    assert {s["key"] for s in bundle["settings"]} == {"feature_flags", "featured_recipe", "etsy_url"}
    assert [r["id"] for r in bundle["recipes"]] == exp.APPROVED_RECIPE_IDS
    assert [p["id"] for p in bundle["printables"]] == exp.APPROVED_PRINTABLE_IDS
    assert "a3f29d4d-16ce-4273-8da7-0c26db31e91a" not in {r["id"] for r in bundle["recipes"]}  # Kabobs (Copy) excluded
    assert all(p["download_count"] == 0 for p in bundle["printables"])
    raw = BUNDLE.read_text()
    for forbidden in ('"_id"', "file_id", "storage_path", "password", "@", "mongodb://", "emergentagent.com"):
        assert forbidden not in raw, forbidden
    manifest = (BACKEND / "content_bundle.manifest.md").read_text()
    assert checksum in manifest and all(r["title"] in manifest for r in bundle["recipes"])


def test_refuses_preview_test_dev_db_names(monkeypatch):
    for name in ("test_database", "kitchen_preview", "dev", "staging_db", "local", "kc_sandbox"):
        with pytest.raises(SystemExit, match="looks like a preview/test/dev"):
            _run(monkeypatch, name, [])


def test_dry_run_default_writes_nothing(monkeypatch, scratch_db):
    out = _run(monkeypatch, SCRATCH, [], app_env="production")
    assert "DRY RUN" in out and f"target DB_NAME : {SCRATCH}" in out
    assert out.count("INSERT recipes") == 6 and out.count("INSERT printables") == 5 and out.count("INSERT settings") == 3
    assert "Rainbow Fruit Kabobs" in out and "502ef474-b8a0-4f5e-8188-d09af0fd0bce" in out
    assert scratch_db.recipes.count_documents({}) == 0 and scratch_db.settings.count_documents({}) == 0


def test_apply_requires_production_env(monkeypatch, scratch_db):
    with pytest.raises(SystemExit, match="APP_ENV=production"):
        _run(monkeypatch, SCRATCH, ["--apply"], app_env=None)
    with pytest.raises(SystemExit, match="APP_ENV=production"):
        _run(monkeypatch, SCRATCH, ["--apply"], app_env="staging")
    assert scratch_db.recipes.count_documents({}) == 0


def test_apply_is_idempotent_and_preserves_uuids(monkeypatch, scratch_db):
    out = _run(monkeypatch, SCRATCH, ["--apply"], app_env="production")
    assert "APPLIED" in out and "14 inserted" in out
    assert scratch_db.recipes.count_documents({}) == 6 and scratch_db.printables.count_documents({}) == 5
    assert scratch_db.settings.count_documents({}) == 3
    assert scratch_db.recipes.find_one({"id": "502ef474-b8a0-4f5e-8188-d09af0fd0bce"})["title"] == "Rainbow Fruit Kabobs"
    assert scratch_db.settings.find_one({"key": "featured_recipe"})["value"]["recipe_id"] == "502ef474-b8a0-4f5e-8188-d09af0fd0bce"
    # Only the three allowed collections exist afterwards
    assert set(scratch_db.list_collection_names()) <= {"recipes", "printables", "settings"}
    out2 = _run(monkeypatch, SCRATCH, ["--apply"], app_env="production")
    assert "0 inserted" in out2 and "14 skipped" in out2
    assert scratch_db.recipes.count_documents({}) == 6


def test_aborts_on_conflicting_content(monkeypatch, scratch_db):
    bundle = json.loads(BUNDLE.read_text())
    doc = dict(bundle["recipes"][0]); doc["title"] = "Something Else Entirely"
    scratch_db.recipes.insert_one(doc)
    with pytest.raises(SystemExit, match="already exists with different content"):
        _run(monkeypatch, SCRATCH, ["--apply"], app_env="production")
    assert scratch_db.recipes.count_documents({}) == 1  # nothing written
    scratch_db.recipes.delete_many({})
    scratch_db.recipes.insert_one({"id": str(uuid.uuid4()), "title": bundle["recipes"][1]["title"]})
    with pytest.raises(SystemExit, match="under a different id"):
        _run(monkeypatch, SCRATCH, [], app_env="production")
    scratch_db.recipes.delete_many({})
    scratch_db.settings.insert_one({"key": "feature_flags", "value": {"personalized_pdf_export": True}})
    with pytest.raises(SystemExit, match="different value"):
        _run(monkeypatch, SCRATCH, [], app_env="production")


def test_bundle_loader_rejects_forbidden_payloads(tmp_path):
    bundle = json.loads(BUNDLE.read_text())
    bad = json.loads(json.dumps(bundle)); bad["users"] = [{"email": "x@y.z"}]
    p = tmp_path / "b.json"; p.write_text(json.dumps(bad))
    with pytest.raises(SystemExit, match="unexpected top-level keys"): imp.load_bundle(p)
    bad = json.loads(json.dumps(bundle)); bad["recipes"][0]["recipe_card_file_id"] = "abc"
    p.write_text(json.dumps(bad))
    with pytest.raises(SystemExit, match="forbidden fields"): imp.load_bundle(p)
    bad = json.loads(json.dumps(bundle)); bad["settings"].append({"key": "logo", "value": {}})
    p.write_text(json.dumps(bad))
    with pytest.raises(SystemExit, match="not allowed"): imp.load_bundle(p)


def test_seed_does_not_insert_starter_content_in_production(monkeypatch):
    for k in ("SEED_STARTER_CONTENT", "APP_ENV", "STRIPE_MODE"): monkeypatch.delenv(k, raising=False)
    sys.path.insert(0, str(BACKEND)); import importlib, seed; seed = importlib.reload(seed)
    assert seed.starter_content_enabled() is False
    monkeypatch.setenv("SEED_STARTER_CONTENT", "true"); assert seed.starter_content_enabled() is True
    monkeypatch.setenv("APP_ENV", "production"); assert seed.starter_content_enabled() is False
    src = (BACKEND / "seed.py").read_text()
    assert "if starter_content_enabled():" in src and "insert_many(RECIPES)" in src.split("if starter_content_enabled():")[1]
