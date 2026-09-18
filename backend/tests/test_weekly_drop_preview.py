"""Admin weekly-drop preview. In-process ASGI client with the email dispatcher patched — no real emails."""
import os
import sys
import uuid
import pytest
import requests
from pathlib import Path
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402  (loads backend/.env)
import email_service  # noqa: E402

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
ADMIN = {"email": "admin@jeanamarie.club", "password": "JeanaAdmin2026!"}
DEMO = {"email": "demo@family.com", "password": "DemoFamily123!"}


_TOKENS = {}
def _live_token(creds):
    if creds["email"] not in _TOKENS:
        r = requests.post(f"{BASE}/auth/login", json=creds); assert r.status_code == 200, r.text
        _TOKENS[creds["email"]] = r.json()["token"]
    return _TOKENS[creds["email"]]


@pytest.fixture
def sent(monkeypatch):
    box = []
    async def fake_dispatch(*, to, subject, html):
        box.append({"to": to, "subject": subject, "html": html})
        return {"provider": "resend", "id": f"fake-{len(box)}"}
    monkeypatch.setattr(email_service, "dispatch_email", fake_dispatch)
    monkeypatch.setattr(server.email_service, "dispatch_email", fake_dispatch)
    return box


@pytest.fixture
def admin_id():
    return server.sync_db.users.find_one({"email": ADMIN["email"]})["id"] if hasattr(server, "sync_db") else None


@pytest.fixture(autouse=True)
def fresh_motor(monkeypatch):
    from motor.motor_asyncio import AsyncIOMotorClient
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    monkeypatch.setattr(server, "db", c[os.environ["DB_NAME"]])
    yield
    c.close()


@pytest.fixture(autouse=True)
def reset_rate_bucket():
    for k in [k for k in list(server._rate_buckets) if k.startswith("drop-preview:")]:
        server._rate_buckets.pop(k, None)
    yield


async def _post(token=None, body=None):
    async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://test") as c:
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return await c.post("/api/admin/email/weekly-drop/preview", headers=h, json=body)


def _snapshot():
    db = server.db.delegate if hasattr(server.db, "delegate") else None
    from pymongo import MongoClient
    pdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    fams = list(pdb.users.find({"role": "family"}, {"_id": 0, "password_hash": 0}))
    settings = list(pdb.settings.find({}, {"_id": 0}))
    recipes = list(pdb.recipes.find({}, {"_id": 0}))
    others = {c: pdb[c].count_documents({}) for c in pdb.list_collection_names() if c not in ("users", "settings", "recipes")}
    return fams, settings, recipes, others


@pytest.mark.anyio
async def test_unauthenticated_401(sent):
    r = await _post(); assert r.status_code in (401, 403) and r.status_code == 401 or r.status_code == 403
    assert sent == []


def test_live_unauthenticated_401_and_non_admin_403():
    assert requests.post(f"{BASE}/admin/email/weekly-drop/preview").status_code in (401, 403)
    r = requests.post(f"{BASE}/admin/email/weekly-drop/preview", headers={"Authorization": f"Bearer {_live_token(DEMO)}"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_recipient_is_admin_and_cannot_be_overridden(sent):
    tok = _live_token(ADMIN)
    r = await _post(tok, {"to": "attacker@example.com", "email": "x@example.com", "recipient": "y@example.com"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recipient"] == ADMIN["email"] and sent[0]["to"] == ADMIN["email"]
    assert "attacker" not in sent[0]["to"]
    assert set(body) == {"ok", "provider", "message_id", "recipient", "recipe"}
    assert body["provider"] == "resend" and body["message_id"] == "fake-1"


@pytest.mark.anyio
async def test_uses_selected_drop_and_production_template(sent):
    from pymongo import MongoClient
    pdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    featured = pdb.settings.find_one({"key": "featured_recipe"}) or {}
    rid = (featured.get("value") or {}).get("recipe_id")
    expected = pdb.recipes.find_one({"id": rid}) if rid else None
    if not expected:
        expected = pdb.recipes.find_one({"is_sample": {"$ne": True}}, sort=[("published_at", -1)])
    r = await _post(_live_token(ADMIN)); assert r.status_code == 200
    m = sent[0]
    assert r.json()["recipe"] == expected["title"]
    assert m["subject"] == f"[PREVIEW] This week: {expected['title']}"
    assert "Admin preview" in m["html"] and "not sent to families" in m["html"]
    # Same template as production, minus banner/prefix
    prod_subject, prod_html = email_service.render_weekly_drop(
        family_name="Jeana Marie", recipe_title=expected["title"], recipe_id=expected["id"], unsubscribe_token="preview")
    assert m["subject"] == f"[PREVIEW] {prod_subject}"
    assert m["html"].replace(email_service.PREVIEW_BANNER, "") == prod_html
    app_url = os.environ["APP_PUBLIC_URL"].rstrip("/")
    assert f'{app_url}/app/recipe/{expected["id"]}' in m["html"]
    assert "preview.emergentagent.com" in app_url  # links point at Preview app


@pytest.mark.anyio
async def test_no_state_changes(sent):
    before = _snapshot()
    r = await _post(_live_token(ADMIN)); assert r.status_code == 200
    assert _snapshot() == before


@pytest.mark.anyio
async def test_rate_limit_five_per_hour(sent):
    tok = _live_token(ADMIN)
    codes = [(await _post(tok)).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]
    assert len(sent) == 5


@pytest.mark.anyio
async def test_provider_failure_is_friendly_string(monkeypatch):
    async def boom(**kw): raise server.HTTPException(status_code=502, detail="Failed to send email")
    monkeypatch.setattr(server.email_service, "dispatch_email", boom)
    r = await _post(_live_token(ADMIN))
    assert r.status_code == 502 and r.json()["detail"] == "Failed to send email"
