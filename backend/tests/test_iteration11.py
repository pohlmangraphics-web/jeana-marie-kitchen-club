"""Iteration 11 backend tests: password reset (email), preferences, unsubscribe,
featured recipe scheduling with fallback, weekly-drop broadcast, and regression."""
import os
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
ADMIN = {"email": "admin@jeanamarie.club", "password": "JeanaAdmin2026!"}
DEMO = {"email": "demo@family.com", "password": "DemoFamily123!"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def demo_token():
    r = requests.post(f"{BASE}/auth/login", json=DEMO, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def H(tok): return {"Authorization": f"Bearer {tok}"}


# --- DB helper for direct verification ---
async def _get_user_field(email, field):
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    u = await db.users.find_one({"email": email})
    cli.close()
    return (u or {}).get(field)


async def _set_user_field(email, field, value):
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    await db.users.update_one({"email": email}, {"$set": {field: value}})
    cli.close()


def db_get(email, field):
    return asyncio.get_event_loop().run_until_complete(_get_user_field(email, field))


def db_set(email, field, value):
    return asyncio.get_event_loop().run_until_complete(_set_user_field(email, field, value))


# --- Forgot password ---
class TestForgotPassword:
    def test_known_email_returns_ok_without_token(self):
        r = requests.post(f"{BASE}/auth/forgot-password", json={"email": ADMIN["email"]}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body == {"ok": True}, f"Expected exact {{ok:true}}, got {body}"
        # DB should have reset_token now
        tok = db_get(ADMIN["email"], "reset_token")
        assert tok and isinstance(tok, str) and len(tok) > 10

    def test_reset_password_with_stored_token(self):
        tok = db_get(ADMIN["email"], "reset_token")
        assert tok
        # Reset to same password to avoid disrupting other tests
        r = requests.post(f"{BASE}/auth/reset-password",
                          json={"token": tok, "new_password": ADMIN["password"]}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # Login still works
        r2 = requests.post(f"{BASE}/auth/login", json=ADMIN, timeout=30)
        assert r2.status_code == 200

    def test_unknown_email_no_enumeration(self):
        r = requests.post(f"{BASE}/auth/forgot-password",
                          json={"email": "nobody-xyz-not-real@example.com"}, timeout=30)
        assert r.status_code == 200
        assert r.json() == {"ok": True}


# --- Preferences ---
class TestPreferences:
    def test_patch_optin_false_then_true(self, demo_token):
        r = requests.patch(f"{BASE}/auth/preferences",
                           headers=H(demo_token), json={"email_optin_weekly": False}, timeout=30)
        assert r.status_code == 200
        me = requests.get(f"{BASE}/auth/me", headers=H(demo_token), timeout=30).json()
        assert me.get("email_optin_weekly") is False
        # restore
        r2 = requests.patch(f"{BASE}/auth/preferences",
                            headers=H(demo_token), json={"email_optin_weekly": True}, timeout=30)
        assert r2.status_code == 200
        me2 = requests.get(f"{BASE}/auth/me", headers=H(demo_token), timeout=30).json()
        assert me2.get("email_optin_weekly") is True


# --- Unsubscribe ---
class TestUnsubscribe:
    def test_invalid_token(self):
        r = requests.get(f"{BASE}/unsubscribe", params={"token": "not-a-real-token"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is False
        assert "Invalid" in body.get("message", "")

    def test_valid_token_flips_optin(self, demo_token):
        # assign unsubscribe_token to demo user directly in db
        test_tok = "test_unsub_iter11_ABC123xyz"
        db_set(DEMO["email"], "unsubscribe_token", test_tok)
        # ensure opted in first
        requests.patch(f"{BASE}/auth/preferences", headers=H(demo_token),
                       json={"email_optin_weekly": True}, timeout=30)
        r = requests.get(f"{BASE}/unsubscribe", params={"token": test_tok}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        # verify optin flipped
        me = requests.get(f"{BASE}/auth/me", headers=H(demo_token), timeout=30).json()
        assert me.get("email_optin_weekly") is False
        # cleanup: restore
        requests.patch(f"{BASE}/auth/preferences", headers=H(demo_token),
                       json={"email_optin_weekly": True}, timeout=30)


# --- Featured recipe scheduling ---
class TestFeatured:
    def test_past_window_falls_back(self, admin_token, demo_token):
        # Pick a real published non-sample recipe id
        recs = requests.get(f"{BASE}/recipes", headers=H(admin_token), timeout=30).json()
        pub = [r for r in recs if not r.get("is_sample")]
        assert pub, "need at least one published non-sample recipe"
        rid = pub[0]["id"]
        r = requests.put(f"{BASE}/admin/featured-recipe", headers=H(admin_token),
                         json={"recipe_id": rid,
                               "starts_at": "2020-01-01T00:00:00+00:00",
                               "ends_at": "2020-01-02T00:00:00+00:00"}, timeout=30)
        assert r.status_code == 200
        got = requests.get(f"{BASE}/recipes/featured", headers=H(demo_token), timeout=30).json()
        assert got.get("fallback") is True
        assert got.get("recipe") is not None
        # fallback recipe is newest non-sample; may or may not equal rid, but we assert fallback=True

    def test_current_window_returns_scheduled(self, admin_token, demo_token):
        recs = requests.get(f"{BASE}/recipes", headers=H(admin_token), timeout=30).json()
        pub = [r for r in recs if not r.get("is_sample")]
        rid = pub[-1]["id"]  # pick a different one from newest to prove not fallback
        r = requests.put(f"{BASE}/admin/featured-recipe", headers=H(admin_token),
                         json={"recipe_id": rid,
                               "starts_at": "2020-01-01T00:00:00+00:00",
                               "ends_at": "2099-01-01T00:00:00+00:00"}, timeout=30)
        assert r.status_code == 200
        got = requests.get(f"{BASE}/recipes/featured", headers=H(demo_token), timeout=30).json()
        assert got.get("fallback") is False
        assert got.get("recipe", {}).get("id") == rid

    def test_null_recipe_falls_back(self, admin_token, demo_token):
        r = requests.put(f"{BASE}/admin/featured-recipe", headers=H(admin_token),
                         json={"recipe_id": None, "starts_at": None, "ends_at": None}, timeout=30)
        assert r.status_code == 200
        got = requests.get(f"{BASE}/recipes/featured", headers=H(demo_token), timeout=30).json()
        assert got.get("fallback") is True
        assert got.get("recipe") is not None

    def test_admin_get_featured(self, admin_token):
        r = requests.get(f"{BASE}/admin/featured-recipe", headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        # keys may be present or empty dict
        assert isinstance(data, dict)


# --- Weekly drop broadcast ---
class TestWeeklyDrop:
    def test_family_forbidden(self, demo_token):
        r = requests.post(f"{BASE}/admin/email/weekly-drop", headers=H(demo_token), timeout=60)
        assert r.status_code == 403

    def test_admin_send(self, admin_token, demo_token):
        # ensure demo user opted in and active
        requests.patch(f"{BASE}/auth/preferences", headers=H(demo_token),
                       json={"email_optin_weekly": True}, timeout=30)
        r = requests.post(f"{BASE}/admin/email/weekly-drop", headers=H(admin_token), timeout=120)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("sent", "skipped_inactive", "failed", "recipe"):
            assert k in body
        assert body["sent"] >= 1, f"expected at least 1 send, got: {body}"


# --- Regression ---
class TestRegression:
    def test_login_admin(self):
        assert requests.post(f"{BASE}/auth/login", json=ADMIN, timeout=30).status_code == 200

    def test_login_demo(self):
        assert requests.post(f"{BASE}/auth/login", json=DEMO, timeout=30).status_code == 200

    def test_samples(self):
        assert requests.get(f"{BASE}/recipes/samples", timeout=30).status_code == 200

    def test_flags(self):
        assert requests.get(f"{BASE}/flags", timeout=30).status_code == 200

    def test_printables(self, demo_token):
        assert requests.get(f"{BASE}/printables", headers=H(demo_token), timeout=30).status_code == 200

    def test_codes_print_sheet(self, admin_token):
        r = requests.get(f"{BASE}/admin/codes/print-sheet.pdf", headers=H(admin_token), timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")


# --- Cleanup ---
def test_zz_cleanup(admin_token, demo_token):
    """Reset featured schedule and ensure demo opted in."""
    requests.put(f"{BASE}/admin/featured-recipe", headers=H(admin_token),
                 json={"recipe_id": None, "starts_at": None, "ends_at": None}, timeout=30)
    requests.patch(f"{BASE}/auth/preferences", headers=H(demo_token),
                   json={"email_optin_weekly": True}, timeout=30)
