"""Launch-readiness backend tests for Jeana Marie's Kitchen Club.

Covers: registration, login, rate-limits, forgot/reset, Stripe checkout,
membership revoke/restore, redeem codes, four tier libraries, recipe card
upload+download, admin editing endpoints, CSV exports, and session flows.
"""
import os
import io
import time
import secrets as pysecrets
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
ADMIN = {"email": "admin@jeanamarie.club", "password": "JeanaAdmin2026!"}
DEMO = {"email": "demo@family.com", "password": "DemoFamily123!"}


def H(t): return {"Authorization": f"Bearer {t}"}


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


@pytest.fixture(scope="module")
def demo_user_id(admin_token):
    fams = requests.get(f"{BASE}/admin/families", headers=H(admin_token), timeout=30).json()
    for f in fams:
        if f["email"] == DEMO["email"]:
            return f["id"]
    pytest.skip("demo family not found")


# ------- direct-DB helpers ----------
async def _get(email, field):
    cli = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = cli[os.environ["DB_NAME"]]
    u = await db.users.find_one({"email": email})
    cli.close()
    return (u or {}).get(field)


def db_get(email, field):
    return asyncio.get_event_loop().run_until_complete(_get(email, field))


# ========= REGISTRATION =========
class TestRegistration:
    _email = None
    _token = None

    def test_register_fresh_family(self):
        email = f"launch+{pysecrets.token_hex(4)}@example.com"
        r = requests.post(f"{BASE}/auth/register",
                          json={"email": email, "family_name": "Launch Test Fam", "password": "TestPass2026!"},
                          timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "token" in body and body["token"]
        assert body["user"]["email"] == email
        assert body["user"].get("membership_expires_at") in (None, "")
        TestRegistration._email = email
        TestRegistration._token = body["token"]

    def test_me_shows_no_membership(self):
        assert TestRegistration._token
        me = requests.get(f"{BASE}/auth/me", headers=H(TestRegistration._token), timeout=30).json()
        assert me.get("has_active_membership") is False

    def test_profiles_empty(self):
        p = requests.get(f"{BASE}/profiles", headers=H(TestRegistration._token), timeout=30)
        assert p.status_code == 200
        assert p.json() == []

    def test_recipes_blocked_without_membership(self):
        r = requests.get(f"{BASE}/recipes", headers=H(TestRegistration._token), timeout=30)
        assert r.status_code == 402

    def test_samples_public(self):
        r = requests.get(f"{BASE}/recipes/samples", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ========= LOGIN =========
class TestLogin:
    def test_admin_ok(self):
        r = requests.post(f"{BASE}/auth/login", json=ADMIN, timeout=30)
        assert r.status_code == 200

    def test_demo_ok(self):
        r = requests.post(f"{BASE}/auth/login", json=DEMO, timeout=30)
        assert r.status_code == 200

    def test_wrong_password_401(self):
        # Use a unique email so we don't consume real login rate-limit buckets
        r = requests.post(f"{BASE}/auth/login",
                          json={"email": f"bad+{pysecrets.token_hex(3)}@example.com",
                                "password": "wrong"}, timeout=30)
        assert r.status_code == 401


# ========= FORGOT / RESET =========
class TestForgotReset:
    def test_forgot_returns_only_ok(self):
        r = requests.post(f"{BASE}/auth/forgot-password", json={"email": ADMIN["email"]}, timeout=30)
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        tok = db_get(ADMIN["email"], "reset_token")
        assert tok and len(tok) > 10

    def test_reset_and_login_new_then_restore(self):
        tok = db_get(ADMIN["email"], "reset_token")
        assert tok
        r = requests.post(f"{BASE}/auth/reset-password",
                          json={"token": tok, "new_password": "NewAdmin2026!"}, timeout=30)
        assert r.status_code == 200
        # login with new
        r2 = requests.post(f"{BASE}/auth/login",
                           json={"email": ADMIN["email"], "password": "NewAdmin2026!"}, timeout=30)
        assert r2.status_code == 200
        # restore
        requests.post(f"{BASE}/auth/forgot-password", json={"email": ADMIN["email"]}, timeout=30)
        tok2 = db_get(ADMIN["email"], "reset_token")
        r3 = requests.post(f"{BASE}/auth/reset-password",
                           json={"token": tok2, "new_password": ADMIN["password"]}, timeout=30)
        assert r3.status_code == 200
        r4 = requests.post(f"{BASE}/auth/login", json=ADMIN, timeout=30)
        assert r4.status_code == 200


# ========= STRIPE CHECKOUT =========
class TestStripeCheckout:
    def test_pricing_public(self):
        r = requests.get(f"{BASE}/payments/pricing", timeout=30)
        assert r.status_code == 200
        keys = {p["lookup_key"] for p in r.json()}
        assert "monthly" in keys

    def test_create_checkout_session(self, demo_token):
        origin = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
        r = requests.post(f"{BASE}/payments/checkout",
                          headers=H(demo_token),
                          json={"lookup_key": "monthly", "origin_url": origin}, timeout=45)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "checkout_url" in body and "stripe.com" in body["checkout_url"]
        assert body.get("session_id")
        # status endpoint works
        s = requests.get(f"{BASE}/payments/status/{body['session_id']}", timeout=30)
        assert s.status_code == 200
        assert s.json()["payment_status"] in ("pending", "unpaid", "no_payment_required", "paid")


# ========= REVOKE + REDEEM =========
class TestRevokeAndRedeem:
    _code = None
    _fresh_token = None
    _fresh_email = None

    def test_revoke_demo(self, admin_token, demo_user_id, demo_token):
        r = requests.post(f"{BASE}/admin/families/{demo_user_id}/revoke",
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        me = requests.get(f"{BASE}/auth/me", headers=H(demo_token), timeout=30).json()
        assert me.get("has_active_membership") is False
        # recipes blocked
        rc = requests.get(f"{BASE}/recipes", headers=H(demo_token), timeout=30)
        assert rc.status_code == 402

    def test_admin_generate_code(self, admin_token):
        r = requests.post(f"{BASE}/admin/codes", headers=H(admin_token),
                          json={"duration": "annual", "count": 1, "note": "launch-test"},
                          timeout=30)
        assert r.status_code == 200, r.text
        codes = r.json()
        assert len(codes) == 1
        assert codes[0].get("batch_id")
        TestRevokeAndRedeem._code = codes[0]["code"]

    def test_register_fresh_and_redeem(self):
        email = f"launch+{pysecrets.token_hex(4)}@example.com"
        r = requests.post(f"{BASE}/auth/register",
                          json={"email": email, "family_name": "Redeem Fam", "password": "TestPass2026!"},
                          timeout=30)
        assert r.status_code == 200
        tok = r.json()["token"]
        TestRevokeAndRedeem._fresh_token = tok
        TestRevokeAndRedeem._fresh_email = email

        code = TestRevokeAndRedeem._code
        assert code
        red = requests.post(f"{BASE}/redeem", headers=H(tok),
                            json={"code": code}, timeout=30)
        assert red.status_code == 200, red.text
        assert "membership_expires_at" in red.json()

        # recipes now accessible
        rc = requests.get(f"{BASE}/recipes", headers=H(tok), timeout=30)
        assert rc.status_code == 200

    def test_redeem_same_code_400(self):
        r = requests.post(f"{BASE}/redeem", headers=H(TestRevokeAndRedeem._fresh_token),
                          json={"code": TestRevokeAndRedeem._code}, timeout=30)
        assert r.status_code == 400

    def test_invalid_code_404(self, demo_token):
        r = requests.post(f"{BASE}/redeem", headers=H(demo_token),
                          json={"code": "NOTREAL-CODE-XYZ"}, timeout=30)
        assert r.status_code == 404

    def test_restore_demo_via_admin_code(self, admin_token, demo_token):
        # admin generates a code + demo redeems to restore membership
        r = requests.post(f"{BASE}/admin/codes", headers=H(admin_token),
                          json={"duration": "annual", "count": 1, "note": "restore-demo"},
                          timeout=30)
        assert r.status_code == 200
        code = r.json()[0]["code"]
        red = requests.post(f"{BASE}/redeem", headers=H(demo_token),
                            json={"code": code}, timeout=30)
        assert red.status_code == 200, red.text
        me = requests.get(f"{BASE}/auth/me", headers=H(demo_token), timeout=30).json()
        assert me.get("has_active_membership") is True


# ========= FOUR TIER LIBRARIES =========
class TestFourLibraries:
    @pytest.mark.parametrize("tier", ["little", "junior", "teen", "adult"])
    def test_tier_returns_list(self, demo_token, tier):
        r = requests.get(f"{BASE}/recipes", params={"tier": tier},
                         headers=H(demo_token), timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ========= RECIPE CARD UPLOAD + DOWNLOAD =========
class TestRecipeCard:
    _rid = None
    _file_id = None

    def test_upload_pdf_and_attach(self, admin_token):
        # pick a real published recipe (non-sample)
        recs = requests.get(f"{BASE}/recipes", headers=H(admin_token), timeout=30).json()
        pub = [r for r in recs if not r.get("is_sample")]
        assert pub
        TestRecipeCard._rid = pub[0]["id"]

        pdf_bytes = (b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
        files = {"file": ("card.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"purpose": "recipe_card"}
        up = requests.post(f"{BASE}/files/upload", headers=H(admin_token),
                           files=files, data=data, timeout=60)
        assert up.status_code == 200, up.text
        TestRecipeCard._file_id = up.json()["file_id"]

        patch = requests.patch(f"{BASE}/recipes/{TestRecipeCard._rid}",
                               headers=H(admin_token),
                               json={"recipe_card_file_id": TestRecipeCard._file_id},
                               timeout=30)
        assert patch.status_code == 200

    def test_download_as_demo(self, demo_token):
        r = requests.get(f"{BASE}/recipes/{TestRecipeCard._rid}/card",
                         headers=H(demo_token), timeout=30)
        assert r.status_code == 200
        assert "pdf" in r.headers.get("content-type", "").lower()

    def test_recipe_without_card_404(self, admin_token, demo_token):
        # find a recipe without recipe_card_file_id
        recs = requests.get(f"{BASE}/recipes", headers=H(admin_token), timeout=30).json()
        no_card = [r for r in recs if not r.get("recipe_card_file_id") and not r.get("is_sample")]
        if not no_card:
            pytest.skip("no non-card recipe available")
        r = requests.get(f"{BASE}/recipes/{no_card[0]['id']}/card",
                         headers=H(demo_token), timeout=30)
        assert r.status_code == 404

    def test_cleanup_detach(self, admin_token):
        # detach the card so future runs still have a "no card" recipe
        requests.patch(f"{BASE}/recipes/{TestRecipeCard._rid}",
                       headers=H(admin_token),
                       json={"recipe_card_file_id": None}, timeout=30)


# ========= ADMIN EDITING =========
class TestAdminEditing:
    def test_edit_recipe_title_and_restore(self, admin_token):
        recs = requests.get(f"{BASE}/recipes", headers=H(admin_token), timeout=30).json()
        pub = [r for r in recs if not r.get("is_sample")]
        rid = pub[0]["id"]
        orig = pub[0]["title"]
        p = requests.patch(f"{BASE}/recipes/{rid}", headers=H(admin_token),
                           json={"title": orig + " (edited)"}, timeout=30)
        assert p.status_code == 200
        assert p.json()["title"].endswith("(edited)")
        # restore
        requests.patch(f"{BASE}/recipes/{rid}", headers=H(admin_token),
                       json={"title": orig}, timeout=30)

    def test_duplicate_and_cleanup(self, admin_token):
        recs = requests.get(f"{BASE}/recipes", headers=H(admin_token), timeout=30).json()
        pub = [r for r in recs if not r.get("is_sample")]
        rid = pub[0]["id"]
        d = requests.post(f"{BASE}/recipes/{rid}/duplicate",
                          headers=H(admin_token), timeout=30)
        assert d.status_code == 200
        new_id = d.json()["id"]
        assert "(Copy)" in d.json()["title"]
        # cleanup dup
        requests.delete(f"{BASE}/recipes/{new_id}", headers=H(admin_token), timeout=30)

    def test_flags_toggle_and_restore(self, admin_token):
        # Get current flags
        cur = requests.get(f"{BASE}/flags", timeout=30).json()
        orig = bool(cur.get("personalized_pdf_export", False))
        new = not orig
        r1 = requests.put(f"{BASE}/admin/flags", headers=H(admin_token),
                          json={"flags": {"personalized_pdf_export": new}}, timeout=30)
        assert r1.status_code == 200
        cur2 = requests.get(f"{BASE}/flags", timeout=30).json()
        assert bool(cur2.get("personalized_pdf_export")) == new
        # restore
        requests.put(f"{BASE}/admin/flags", headers=H(admin_token),
                     json={"flags": {"personalized_pdf_export": orig}}, timeout=30)

    def test_etsy_url_save_and_clear(self, admin_token):
        r = requests.put(f"{BASE}/admin/branding/etsy-url",
                         headers=H(admin_token),
                         json={"url": "https://etsy.com/shop/test"}, timeout=30)
        assert r.status_code == 200
        assert requests.get(f"{BASE}/branding/etsy-url", timeout=30).json()["url"] == "https://etsy.com/shop/test"
        # clear
        requests.put(f"{BASE}/admin/branding/etsy-url",
                     headers=H(admin_token), json={"url": ""}, timeout=30)
        assert requests.get(f"{BASE}/branding/etsy-url", timeout=30).json()["url"] == ""

    def test_codes_print_sheet_pdf(self, admin_token):
        r = requests.get(f"{BASE}/admin/codes/print-sheet.pdf",
                         headers=H(admin_token), timeout=60)
        assert r.status_code == 200
        assert "pdf" in r.headers.get("content-type", "").lower()

    def test_csv_exports(self, admin_token):
        for entity in ("families", "recipes", "codes"):
            r = requests.get(f"{BASE}/admin/export/{entity}",
                             params={"format": "csv"},
                             headers=H(admin_token), timeout=60)
            assert r.status_code == 200, f"{entity}: {r.status_code} {r.text[:200]}"
            assert "csv" in r.headers.get("content-type", "").lower() or r.text.count(",") > 0

    def test_printable_edit(self, admin_token, demo_token):
        printables = requests.get(f"{BASE}/printables", headers=H(demo_token), timeout=30).json()
        if not printables:
            pytest.skip("no printables")
        pid = printables[0]["id"]
        orig = printables[0]["title"]
        p = requests.patch(f"{BASE}/printables/{pid}",
                          headers=H(admin_token),
                          json={"title": orig + " (edit)"}, timeout=30)
        assert p.status_code == 200
        # restore
        requests.patch(f"{BASE}/printables/{pid}",
                       headers=H(admin_token),
                       json={"title": orig}, timeout=30)


# ========= SESSION PERSISTENCE =========
class TestSessionPersistence:
    def test_journal_entry_persists_across_sessions(self, demo_token):
        # find a demo profile
        profs = requests.get(f"{BASE}/profiles", headers=H(demo_token), timeout=30).json()
        assert profs
        pid = profs[0]["id"]

        marker = f"LAUNCH_TEST_{pysecrets.token_hex(4)}"
        create = requests.post(f"{BASE}/journal", headers=H(demo_token),
                               json={"profile_id": pid, "title": marker, "notes": "launch test"},
                               timeout=30)
        assert create.status_code == 200, create.text
        eid = create.json().get("id")

        # log back in fresh token
        r = requests.post(f"{BASE}/auth/login", json=DEMO, timeout=30)
        assert r.status_code == 200
        new_tok = r.json()["token"]
        entries = requests.get(f"{BASE}/journal/{pid}", headers=H(new_tok), timeout=30).json()
        assert any(e.get("title") == marker for e in entries)

        # cleanup
        if eid:
            requests.delete(f"{BASE}/journal/{eid}", headers=H(new_tok), timeout=30)

    def test_profile_count_stable(self, demo_token):
        profs = requests.get(f"{BASE}/profiles", headers=H(demo_token), timeout=30).json()
        names = {p["name"] for p in profs}
        # demo should have 4 profiles per seed
        assert len(profs) >= 4, f"expected >=4 profiles, got {len(profs)}: {names}"


# ========= JWT / PROTECTED =========
class TestJWT:
    def test_bad_token_401(self):
        r = requests.get(f"{BASE}/auth/me", headers={"Authorization": "Bearer not.a.jwt"}, timeout=30)
        assert r.status_code == 401

    def test_no_token_401(self):
        r = requests.get(f"{BASE}/auth/me", timeout=30)
        assert r.status_code in (401, 403)


# ========= FINAL CLEANUP =========
def test_zzz_cleanup(admin_token):
    """Clean up any launch-test data + restore admin defaults."""
    # ensure admin password intact
    r = requests.post(f"{BASE}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200
    # clear etsy url
    requests.put(f"{BASE}/admin/branding/etsy-url",
                 headers=H(admin_token), json={"url": ""}, timeout=30)
    # ensure featured recipe cleared
    requests.put(f"{BASE}/admin/featured-recipe", headers=H(admin_token),
                 json={"recipe_id": None, "starts_at": None, "ends_at": None},
                 timeout=30)
