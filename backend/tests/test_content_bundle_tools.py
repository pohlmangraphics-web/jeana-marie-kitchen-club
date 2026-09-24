"""Migration tooling tests. Uses a scratch Mongo DB (created + dropped here) and an in-memory fake object store;
never touches Preview/Live data. One opt-in test round-trips through real storage under a scratch APP_NAME."""
import io
import json
import os
import re
import shutil
import sys
import uuid
import hashlib
import contextlib
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pymongo import MongoClient
from PIL import Image
from pypdf import PdfReader

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env")
sys.path.insert(0, str(BACKEND / "tools")); sys.path.insert(0, str(BACKEND))
import import_content_bundle as imp  # noqa: E402
import export_content_bundle as exp  # noqa: E402

BUNDLE = BACKEND / "content_bundle.json"
ASSETS = BACKEND / "content_bundle_assets"
SCRATCH = f"kitchen_club_prod_scratch_{uuid.uuid4().hex[:6]}"  # must NOT match the unsafe-name pattern
FAKE_LIVE = "https://club.example-live.com"
PREVIEW_HOST = re.sub(r"^https?://", "", os.environ["APP_PUBLIC_URL"]).strip("/")
COOKIE_ID = "b22919be-b09d-4e79-b73c-d6484e3ae5d9"
BURGERS_ID = "1bdb483c-986c-4dbc-bfe3-021b29d48e0d"
ORIGINAL_JOE = Path("/app/memory/launch_recipes/joe-helping.webp")
ORIGINAL_JOE_SHA = "90a0900a584535e23d05013c5803cb0bddab8d669364e0a7c72fe6d7febdfe7e"


def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


@pytest.fixture
def scratch_db():
    c = MongoClient(os.environ["MONGO_URL"]); db = c[SCRATCH]
    yield db
    c.drop_database(SCRATCH)


@pytest.fixture
def fake_store(monkeypatch):
    store = {}
    def put(path, data, ct): store[path] = (bytes(data), ct); return {"path": path, "size": len(data)}
    def get(path): return store[path]
    def delete(path): return store.pop(path, None) is not None
    monkeypatch.setattr(imp.storage, "put_object", put); monkeypatch.setattr(imp.storage, "get_object", get)
    monkeypatch.setattr(imp.storage, "delete_object", delete)
    return store


def _run(monkeypatch, db_name, argv, app_env=None, public_url=FAKE_LIVE, bundle=None):
    monkeypatch.setenv("DB_NAME", db_name)
    if app_env is None: monkeypatch.delenv("APP_ENV", raising=False)
    else: monkeypatch.setenv("APP_ENV", app_env)
    if public_url is None: monkeypatch.delenv("APP_PUBLIC_URL", raising=False)
    else: monkeypatch.setenv("APP_PUBLIC_URL", public_url)
    monkeypatch.setattr(sys, "argv", ["import_content_bundle.py"] + (["--bundle", str(bundle)] if bundle else []) + argv)
    monkeypatch.setattr(imp, "load_dotenv", lambda *_a, **_k: None)  # env comes from the test, not .env
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        imp.main()
    return out.getvalue()


def _copy_bundle(tmp_path) -> Path:
    b = tmp_path / "content_bundle.json"; shutil.copy(BUNDLE, b)
    shutil.copytree(ASSETS, tmp_path / "content_bundle_assets")
    return b


def _apply_all(monkeypatch, argv=("--apply",), bundle=None):
    return _run(monkeypatch, SCRATCH, list(argv), app_env="production", bundle=bundle)


# ------------------------------------------------------------------ bundle / export shape
def test_bundle_shape_and_exclusions():
    bundle, checksum = imp.load_bundle(BUNDLE)
    assert len(bundle["recipes"]) == 11 and len(bundle["printables"]) == 2 and len(bundle["assets"]) == 6
    assert {s["key"] for s in bundle["settings"]} == {"feature_flags", "featured_recipe", "etsy_url"}
    assert [r["id"] for r in bundle["recipes"]] == exp.APPROVED_RECIPE_IDS
    assert [p["id"] for p in bundle["printables"]] == exp.APPROVED_PRINTABLE_IDS
    assert "a3f29d4d-16ce-4273-8da7-0c26db31e91a" not in {r["id"] for r in bundle["recipes"]}  # Kabobs (Copy) excluded
    assert all(p["download_count"] == 0 for p in bundle["printables"])
    assert all(r.get("tier") != "adult" for r in bundle["recipes"])
    raw = BUNDLE.read_text() + (BACKEND / "content_bundle.manifest.md").read_text()
    for forbidden in ('"_id"', "file_id", "storage_path", "password", "@", "mongodb://", "emergentagent.com", "/api/files/", PREVIEW_HOST):
        assert forbidden not in raw, forbidden
    assert checksum in (BACKEND / "content_bundle.manifest.md").read_text()


def test_asset_count_ownership_and_manifest_fields():
    bundle, _ = imp.load_bundle(BUNDLE)
    photos = [a for a in bundle["assets"] if a["purpose"] == "recipe_photo"]
    pdfs = [a for a in bundle["assets"] if a["purpose"] == "printable_pdf"]
    assert len(photos) == 4 and len(pdfs) == 2
    assert {a["owner_id"] for a in photos} == {"aba6b0a7-e6a3-4ce7-a017-bd71fad6a68c", COOKIE_ID,
                                               "da3235b8-771b-4a74-9289-5372d9eed7f8", "593b7e51-26b4-4254-89e3-0a8fdc14a239"}
    assert {a["owner_id"] for a in pdfs} == set(exp.APPROVED_PRINTABLE_IDS)
    assert all(a["collection"] == "recipes" and a["content_type"] == "image/jpeg" for a in photos)
    assert all(a["collection"] == "printables" and a["content_type"] == "application/pdf" for a in pdfs)
    assert all(set(a) == imp.ASSET_KEYS for a in bundle["assets"])
    assert {p.name for p in ASSETS.iterdir()} == {a["filename"] for a in bundle["assets"]}
    for a in bundle["assets"]:
        data = (ASSETS / a["filename"]).read_bytes()
        assert len(data) == a["size"] and sha(data) == a["sha256"]
    # every asset-backed recipe carries a marker; the Unsplash-backed burgers URL is untouched
    by_id = {r["id"]: r for r in bundle["recipes"]}
    for a in photos: assert by_id[a["owner_id"]]["photo_url"] == f"asset:{a['sha256']}"
    src = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    live_burgers = src.recipes.find_one({"id": BURGERS_ID}, {"_id": 0, "photo_url": 1})["photo_url"]
    assert by_id[BURGERS_ID]["photo_url"] == live_burgers and live_burgers.startswith("https://images.unsplash.com/")
    assert sum("/api/files/" in json.dumps(r) for r in bundle["recipes"]) == 0


def test_cookie_crop_is_face_focused_landscape_and_original_untouched():
    bundle, _ = imp.load_bundle(BUNDLE)
    a = next(x for x in bundle["assets"] if x["owner_id"] == COOKIE_ID)
    data = (ASSETS / a["filename"]).read_bytes()
    im = Image.open(io.BytesIO(data)); assert im.format == "JPEG" and im.width > im.height
    assert ORIGINAL_JOE.exists() and sha(ORIGINAL_JOE.read_bytes()) == ORIGINAL_JOE_SHA
    # The approved crop is the top 1500x1000 region (face + scoop, above the torso) of the untouched original
    orig = Image.open(ORIGINAL_JOE).convert("RGB").crop((0, 0, 1500, 1000))
    assert im.size == orig.size == (1500, 1000)
    diff = sum(abs(p - q) for p, q in zip(orig.resize((30, 20)).tobytes(), im.convert("RGB").resize((30, 20)).tobytes())) / (30 * 20 * 3)
    assert diff < 6, f"crop diverges from approved region (mean abs diff {diff})"
    # Renders inside the landscape recipe-card frame via the generator
    import recipe_card
    src = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    recipe = src.recipes.find_one({"id": COOKIE_ID}, {"_id": 0})
    pdf, meta = recipe_card.build_recipe_card(recipe, get_object=lambda _fid: (data, "image/jpeg"))
    assert pdf.startswith(b"%PDF") and len(PdfReader(io.BytesIO(pdf)).pages) >= 1


def test_printable_pdfs_are_valid_one_page_nonblank():
    bundle, _ = imp.load_bundle(BUNDLE)
    for a in (x for x in bundle["assets"] if x["purpose"] == "printable_pdf"):
        reader = PdfReader(io.BytesIO((ASSETS / a["filename"]).read_bytes()))
        assert len(reader.pages) == 1
        page = reader.pages[0]
        content = page.get_contents().get_data() if page.get_contents() is not None else b""
        assert len(content) > 500 or len(page.extract_text().strip()) > 20 or "/XObject" in str(page.get("/Resources", {}))


# ------------------------------------------------------------------ safety refusals
def test_refuses_preview_test_dev_db_names(monkeypatch, fake_store):
    for name in ("test_database", "kitchen_preview", "dev", "staging_db", "local", "kc_sandbox"):
        with pytest.raises(SystemExit, match="looks like a preview/test/dev"):
            _run(monkeypatch, name, [])


def test_refuses_unsafe_public_url(monkeypatch, scratch_db, fake_store):
    for url in (None, "http://club.example.com", os.environ["APP_PUBLIC_URL"], "https://localhost:3000",
                "https://staging.club.com", "https://club.dev.example.com", "https://club.example.com/path?x=1"):
        with pytest.raises(SystemExit, match="APP_PUBLIC_URL"):
            _run(monkeypatch, SCRATCH, [], app_env="production", public_url=url)
    assert scratch_db.recipes.count_documents({}) == 0


def test_dry_run_default_writes_nothing(monkeypatch, scratch_db, fake_store):
    out = _run(monkeypatch, SCRATCH, [], app_env="production")
    assert "DRY RUN" in out and f"target DB_NAME : {SCRATCH}" in out and f"public URL     : {FAKE_LIVE}" in out
    assert out.count("INSERT recipes") == 11 and out.count("INSERT printables") == 2 and out.count("INSERT settings") == 3
    assert out.count("UPLOAD asset") == 6
    assert scratch_db.recipes.count_documents({}) == 0 and scratch_db.files.count_documents({}) == 0 and fake_store == {}


def test_apply_requires_production_env(monkeypatch, scratch_db, fake_store):
    with pytest.raises(SystemExit, match="APP_ENV=production"):
        _run(monkeypatch, SCRATCH, ["--apply"], app_env=None)
    with pytest.raises(SystemExit, match="APP_ENV=production"):
        _run(monkeypatch, SCRATCH, ["--apply"], app_env="staging")
    assert scratch_db.recipes.count_documents({}) == 0 and fake_store == {}


# ------------------------------------------------------------------ apply into scratch
def test_apply_imports_content_and_assets_then_second_run_is_noop(monkeypatch, scratch_db, fake_store):
    bundle, _ = imp.load_bundle(BUNDLE)
    preview_file_ids = {f["id"] for f in MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]].files.find({}, {"id": 1})}
    out = _apply_all(monkeypatch)
    assert "APPLIED" in out and "6 assets uploaded" in out and "16 inserted" in out
    assert scratch_db.recipes.count_documents({}) == 11 and scratch_db.printables.count_documents({}) == 2
    assert scratch_db.settings.count_documents({}) == 3 and scratch_db.files.count_documents({}) == 6
    assert set(scratch_db.list_collection_names()) <= {"recipes", "printables", "settings", "files"}
    assert scratch_db.settings.find_one({"key": "featured_recipe"})["value"]["recipe_id"] == "502ef474-b8a0-4f5e-8188-d09af0fd0bce"
    for a in bundle["assets"]:
        field = imp.ASSET_RULES[a["purpose"]][1]
        doc = scratch_db[a["collection"]].find_one({"id": a["owner_id"]}, {"_id": 0})
        fid = doc[field]
        assert imp.UUID.match(fid) and fid not in preview_file_ids
        rec = scratch_db.files.find_one({"id": fid}, {"_id": 0})
        assert rec and rec["purpose"] == a["purpose"] and rec["sha256"] == a["sha256"] and rec["owner_id"] == a["owner_id"]
        assert rec["owner_collection"] == a["collection"] and rec["safe_filename"] == a["filename"] and rec["size"] == a["size"]
        assert PREVIEW_HOST not in rec["storage_path"] and "content_bundle_import" in rec["storage_path"]
        stored, _ = fake_store[rec["storage_path"]]
        assert sha(stored) == a["sha256"] and stored == (ASSETS / a["filename"]).read_bytes()
        if a["collection"] == "recipes":
            assert doc["photo_url"] == f"{FAKE_LIVE}/api/files/{fid}"
    dump = json.dumps([d for c in ("recipes", "printables", "files") for d in scratch_db[c].find({}, {"_id": 0})])
    assert "asset:" not in dump and PREVIEW_HOST not in dump and "emergentagent.com" not in dump
    assert scratch_db.recipes.find_one({"id": BURGERS_ID})["photo_url"].startswith("https://images.unsplash.com/")
    assert out.count("OK recipes") == 4 and out.count("OK printables") == 2
    # second identical run: nothing uploaded, everything skipped
    before = {c: list(scratch_db[c].find({}, {"_id": 0})) for c in ("recipes", "printables", "settings", "files")}
    out2 = _apply_all(monkeypatch)
    assert "0 assets uploaded, 6 assets skipped, 0 inserted, 16 skipped" in out2 and out2.count("SKIP   asset") == 6
    assert {c: list(scratch_db[c].find({}, {"_id": 0})) for c in before} == before and len(fake_store) == 6


def test_partial_failure_cleans_up_only_new_artefacts_and_rerun_resumes(monkeypatch, scratch_db, fake_store):
    calls = {"n": 0}
    real_put = imp.storage.put_object
    def flaky_put(path, data, ct):
        calls["n"] += 1
        if calls["n"] == 3: raise RuntimeError("simulated storage outage")
        return real_put(path, data, ct)
    monkeypatch.setattr(imp.storage, "put_object", flaky_put)
    with pytest.raises(SystemExit, match="failed during upload/record"):
        _apply_all(monkeypatch)
    # two assets + their owners landed; the failing one left no record and no object
    assert scratch_db.files.count_documents({}) == 2 and len(fake_store) == 2 and scratch_db.recipes.count_documents({}) == 8  # 6 asset-less recipes + 2 with assets
    # a genuinely-existing, unrelated target record must survive any cleanup
    scratch_db.files.insert_one({"id": "keep-me", "uploaded_by": "someone-else", "is_deleted": False})
    monkeypatch.setattr(imp.storage, "put_object", real_put)
    out = _apply_all(monkeypatch)
    assert "4 assets uploaded, 2 assets skipped" in out and scratch_db.files.count_documents({"id": "keep-me"}) == 1
    assert scratch_db.recipes.count_documents({}) == 11 and scratch_db.files.count_documents({}) == 7


def test_aborts_on_conflicting_content(monkeypatch, scratch_db, fake_store):
    bundle = json.loads(BUNDLE.read_text())
    doc = dict(bundle["recipes"][0]); doc["title"] = "Something Else Entirely"
    scratch_db.recipes.insert_one(doc)
    with pytest.raises(SystemExit, match="already exists with different content"):
        _apply_all(monkeypatch)
    assert scratch_db.recipes.count_documents({}) == 1 and fake_store == {}  # nothing written
    scratch_db.recipes.delete_many({})
    scratch_db.recipes.insert_one({"id": str(uuid.uuid4()), "title": bundle["recipes"][1]["title"]})
    with pytest.raises(SystemExit, match="under a different id"):
        _run(monkeypatch, SCRATCH, [], app_env="production")
    scratch_db.recipes.delete_many({})
    scratch_db.settings.insert_one({"key": "feature_flags", "value": {"personalized_pdf_export": True}})
    with pytest.raises(SystemExit, match="different value"):
        _run(monkeypatch, SCRATCH, [], app_env="production")
    scratch_db.settings.delete_many({})
    # existing asset for the same owner/purpose with a different hash
    a = bundle["assets"][0]
    scratch_db.files.insert_one({"id": "x", "owner_collection": a["collection"], "owner_id": a["owner_id"], "purpose": a["purpose"],
                                 "sha256": "0" * 64, "is_deleted": False})
    with pytest.raises(SystemExit, match="different SHA-256"):
        _run(monkeypatch, SCRATCH, [], app_env="production")
    scratch_db.files.delete_many({})
    # owner record present but its asset missing from the target
    scratch_db.recipes.insert_one(dict(bundle["recipes"][6]))
    with pytest.raises(SystemExit, match="asset is missing from the target"):
        _run(monkeypatch, SCRATCH, [], app_env="production")
    assert fake_store == {}


def test_asset_tampering_aborts_before_any_write(monkeypatch, scratch_db, fake_store, tmp_path):
    def fresh(name):
        d = tmp_path / name; d.mkdir(); return _copy_bundle(d)
    def expect(b, pattern):
        with pytest.raises(SystemExit, match=pattern): _apply_all(monkeypatch, bundle=b)
        assert scratch_db.recipes.count_documents({}) == 0 and scratch_db.files.count_documents({}) == 0 and fake_store == {}
    def edit(b, fn):
        data = json.loads(b.read_text()); fn(data); b.write_text(json.dumps(data)); return b
    bundle = json.loads(BUNDLE.read_text()); first = bundle["assets"][0]["filename"]; pdf = bundle["assets"][4]["filename"]
    b = fresh("missing"); (b.parent / "content_bundle_assets" / first).unlink(); expect(b, "missing asset files")
    b = fresh("extra"); (b.parent / "content_bundle_assets" / "stray.jpg").write_bytes(b"\xff\xd8\xff"); expect(b, "extra unmanifested")
    b = fresh("altered"); p = b.parent / "content_bundle_assets" / first; p.write_bytes(p.read_bytes() + b"x"); expect(b, "size")
    b = fresh("altered_same_size"); p = b.parent / "content_bundle_assets" / first; d = bytearray(p.read_bytes()); d[-1] ^= 1; p.write_bytes(bytes(d)); expect(b, "SHA-256")
    b = fresh("wrong_mime"); p = b.parent / "content_bundle_assets" / pdf; p.write_bytes(p.read_bytes()); expect(edit(b, lambda d: d["assets"].__setitem__(4, {**d["assets"][4], "content_type": "image/jpeg"})), "MIME")
    b = fresh("swapped_bytes"); p = b.parent / "content_bundle_assets" / first; jpg = p.read_bytes(); p2 = b.parent / "content_bundle_assets" / pdf; pdfb = p2.read_bytes()
    expect(edit(b, lambda d: d["assets"].__setitem__(0, {**d["assets"][0], "size": len(pdfb), "sha256": sha(pdfb)})), "SHA-256|MIME|duplicate")
    for bad in ("../evil.jpg", "/abs/evil.jpg", "sub/evil.jpg", "..jpg", "evil.exe", "a b.jpg"):
        b = fresh("trav" + str(abs(hash(bad)))); expect(edit(b, lambda d, bad=bad: d["assets"][0].__setitem__("filename", bad)), "unsafe asset filename|MIME")
    b = fresh("dup"); expect(edit(b, lambda d: d["assets"].append(dict(d["assets"][0]))), "duplicate asset")
    b = fresh("unmanifested_marker"); expect(edit(b, lambda d: d["recipes"][6].__setitem__("photo_url", "asset:" + "a" * 64)), "does not match an asset")
    b = fresh("foreign_owner"); expect(edit(b, lambda d: d["assets"][0].__setitem__("owner_id", str(uuid.uuid4()))), "not a recipes document")
    b = fresh("preview_url"); expect(edit(b, lambda d: d["recipes"][6].__setitem__("photo_url", f"https://{PREVIEW_HOST}/x.jpg")), "forbidden text|safe https")
    b = fresh("orphan_asset"); expect(edit(b, lambda d: d["recipes"][6].__setitem__("photo_url", d["recipes"][0]["photo_url"])), "unreferenced")
    b = fresh("bad_purpose"); expect(edit(b, lambda d: d["assets"][0].__setitem__("purpose", "recipe_card")), "not allowed")
    b = fresh("users"); expect(edit(b, lambda d: d.__setitem__("users", [{"email": "x@y.z"}])), "unexpected top-level keys")
    b = fresh("file_field"); expect(edit(b, lambda d: d["recipes"][0].__setitem__("recipe_card_file_id", "abc")), "forbidden fields")
    b = fresh("setting"); expect(edit(b, lambda d: d["settings"].append({"key": "logo", "value": {}})), "not allowed")
    b = fresh("no_assets_dir"); shutil.rmtree(b.parent / "content_bundle_assets"); expect(b, "assets directory")


def test_export_blocks_preview_hostnames_and_hidden_printables(monkeypatch):
    src = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    monkeypatch.setattr(exp, "APPROVED_RECIPE_IDS", exp.APPROVED_RECIPE_IDS[:6])  # asset-less recipes only
    monkeypatch.setattr(exp, "APPROVED_PRINTABLE_IDS", ["73e0b3f0-a355-405e-ac12-4616b63a88ce"])  # hidden Shopping List
    with pytest.raises(SystemExit, match="hidden"): exp.build_bundle(src, get_object=lambda p: (b"", ""))
    text = BUNDLE.read_text()
    assert not re.search(r"https?://[^\"]*/api/files/", text)
    assert text.count("asset:") == 4


@pytest.mark.skipif(not os.environ.get("EMERGENT_LLM_KEY"), reason="real object storage not configured")
def test_real_storage_roundtrip_under_scratch_app_name(monkeypatch, scratch_db):
    monkeypatch.setenv("APP_NAME", f"kitchen-club-prod-scratch-{uuid.uuid4().hex[:6]}")
    out = _apply_all(monkeypatch)
    assert "6 assets uploaded" in out and out.count("OK ") == 6
    bundle, _ = imp.load_bundle(BUNDLE)
    for a in bundle["assets"]:
        rec = scratch_db.files.find_one({"owner_id": a["owner_id"], "purpose": a["purpose"]}, {"_id": 0})
        assert rec["storage_path"].startswith(os.environ["APP_NAME"] + "/")
        data, _ = imp.storage.get_object(rec["storage_path"])
        assert sha(data) == a["sha256"] and data == (ASSETS / a["filename"]).read_bytes()


def test_seed_does_not_insert_starter_content_in_production(monkeypatch):
    for k in ("SEED_STARTER_CONTENT", "APP_ENV", "STRIPE_MODE"): monkeypatch.delenv(k, raising=False)
    import importlib, seed; seed = importlib.reload(seed)
    assert seed.starter_content_enabled() is False
    monkeypatch.setenv("SEED_STARTER_CONTENT", "true"); assert seed.starter_content_enabled() is True
    monkeypatch.setenv("APP_ENV", "production"); assert seed.starter_content_enabled() is False
    src = (BACKEND / "seed.py").read_text()
    assert "if starter_content_enabled():" in src and "insert_many(RECIPES)" in src.split("if starter_content_enabled():")[1]
