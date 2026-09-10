"""Jeana Marie's Kitchen Club - Backend API test suite (pytest)."""
import os
import io
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://recipe-journal-club.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@jeanamarie.club"
ADMIN_PW = "JeanaAdmin2026!"
DEMO_EMAIL = "demo@family.com"
DEMO_PW = "DemoFamily123!"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "admin"
    return data["token"]


@pytest.fixture(scope="session")
def demo_token():
    r = requests.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PW})
    assert r.status_code == 200, f"demo login failed: {r.text}"
    return r.json()["token"]


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- feature flags ----------
class TestFlags:
    def test_public_flags(self):
        r = requests.get(f"{API}/flags")
        assert r.status_code == 200
        flags = r.json()
        assert flags["kid_photo_upload"] is False
        assert flags["personalized_pdf_export"] is False
        assert flags["stripe_checkout"] is True
        assert flags["printables"] is True


# ---------- auth ----------
class TestAuth:
    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_register_short_password_fails(self):
        r = requests.post(f"{API}/auth/register",
                          json={"email": f"TEST_short_{uuid.uuid4().hex[:6]}@ex.com",
                                "password": "abc123", "family_name": "TEST"})
        assert r.status_code == 422

    def test_register_success(self):
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@ex.com"
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "abcdefgh1", "family_name": "TEST Family"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "token" in d and d["user"]["email"] == email.lower()
        assert d["user"]["role"] == "family"

    def test_login_rate_limit(self):
        email = f"TEST_rl_{uuid.uuid4().hex[:6]}@ex.com"
        # register a real user first
        requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "abcdefgh1", "family_name": "RL"})
        # forge a unique client IP so the per-IP bucket is isolated from other tests / real traffic
        fake_ip = f"203.0.113.{uuid.uuid4().int % 250 + 1}"
        headers = {"X-Forwarded-For": fake_ip}
        codes = []
        for _ in range(7):
            rr = requests.post(f"{API}/auth/login",
                               json={"email": email, "password": "WRONGxxxxx"},
                               headers=headers)
            codes.append(rr.status_code)
        # After 5 failed 401s, the 6th & 7th MUST be 429 (per rate_limit(..., 5, 300))
        assert codes[:5] == [401] * 5, f"first 5 should be 401, got {codes}"
        assert 429 in codes[5:], f"expected 429 on 6th+ attempt, got {codes}"

    def test_register_rate_limit(self):
        """POST /api/auth/register is rate-limited to 10/hour per real client IP."""
        fake_ip = f"198.51.100.{uuid.uuid4().int % 250 + 1}"
        headers = {"X-Forwarded-For": fake_ip}
        codes = []
        for i in range(12):
            email = f"TEST_regrl_{uuid.uuid4().hex[:8]}@ex.com"
            rr = requests.post(f"{API}/auth/register",
                               json={"email": email, "password": "abcdefgh1", "family_name": "RRL"},
                               headers=headers)
            codes.append(rr.status_code)
        assert 429 in codes, f"expected 429 in register burst, got {codes}"

    def test_forgot_password_rate_limit(self):
        """POST /api/auth/forgot-password is rate-limited to 5/hour per real client IP."""
        fake_ip = f"192.0.2.{uuid.uuid4().int % 250 + 1}"
        headers = {"X-Forwarded-For": fake_ip}
        codes = []
        for _ in range(7):
            rr = requests.post(f"{API}/auth/forgot-password",
                               json={"email": f"nobody_{uuid.uuid4().hex[:6]}@ex.com"},
                               headers=headers)
            codes.append(rr.status_code)
        assert 429 in codes, f"expected 429 in forgot-password burst, got {codes}"

    def test_reset_password_rate_limit(self):
        """POST /api/auth/reset-password is rate-limited to 10/hour per real client IP."""
        fake_ip = f"198.18.0.{uuid.uuid4().int % 250 + 1}"
        headers = {"X-Forwarded-For": fake_ip}
        codes = []
        for _ in range(12):
            rr = requests.post(f"{API}/auth/reset-password",
                               json={"token": "invalid-" + uuid.uuid4().hex, "new_password": "abcdefgh1"},
                               headers=headers)
            codes.append(rr.status_code)
        assert 429 in codes, f"expected 429 in reset-password burst, got {codes}"

    def test_real_ip_helper_parses_xff_first_value(self):
        """Two requests with different XFF first-values must land in different rate-limit buckets.

        If real_ip() incorrectly used request.client.host (or a later XFF value),
        both bursts would share a bucket and only the first would hit 429.
        Since XFF first-value differs, both bursts should be able to reach 429 independently.
        """
        # First burst -> should trigger 429 with its own IP
        ip_a = f"203.0.113.{uuid.uuid4().int % 250 + 1}"
        email_a = f"TEST_xffa_{uuid.uuid4().hex[:6]}@ex.com"
        requests.post(f"{API}/auth/register",
                      json={"email": email_a, "password": "abcdefgh1", "family_name": "XA"})
        codes_a = []
        for _ in range(7):
            r = requests.post(f"{API}/auth/login",
                              json={"email": email_a, "password": "WRONGxxxxx"},
                              headers={"X-Forwarded-For": f"{ip_a}, 10.0.0.1, 10.0.0.2"})
            codes_a.append(r.status_code)
        assert 429 in codes_a, f"burst A should hit 429, got {codes_a}"

        # Second burst with different first-value XFF -> fresh bucket, first 5 must be 401
        ip_b = f"203.0.113.{(uuid.uuid4().int + 128) % 250 + 1}"
        while ip_b == ip_a:
            ip_b = f"203.0.113.{(uuid.uuid4().int + 200) % 250 + 1}"
        email_b = f"TEST_xffb_{uuid.uuid4().hex[:6]}@ex.com"
        requests.post(f"{API}/auth/register",
                      json={"email": email_b, "password": "abcdefgh1", "family_name": "XB"})
        codes_b = []
        for _ in range(5):
            r = requests.post(f"{API}/auth/login",
                              json={"email": email_b, "password": "WRONGxxxxx"},
                              headers={"X-Forwarded-For": f"{ip_b}, 10.0.0.9"})
            codes_b.append(r.status_code)
        assert codes_b == [401] * 5, (
            f"burst B (different XFF first-value) must NOT share bucket with A; got {codes_b}"
        )

    def test_forgot_password_returns_token_when_user_exists(self):
        email = f"TEST_fp_{uuid.uuid4().hex[:8]}@ex.com"
        requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "abcdefgh1", "family_name": "FP"})
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        d = r.json()
        assert d.get("reset_token"), "reset_token missing"

    def test_forgot_password_nonexistent_no_token(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"nope_{uuid.uuid4().hex[:8]}@ex.com"})
        assert r.status_code == 200
        assert "reset_token" not in r.json()

    def test_reset_password_valid_then_invalid(self):
        email = f"TEST_rp_{uuid.uuid4().hex[:8]}@ex.com"
        requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "abcdefgh1", "family_name": "RP"})
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        tok = r.json()["reset_token"]
        r2 = requests.post(f"{API}/auth/reset-password",
                           json={"token": tok, "new_password": "newpass123"})
        assert r2.status_code == 200
        # login with new
        rl = requests.post(f"{API}/auth/login", json={"email": email, "password": "newpass123"})
        assert rl.status_code == 200
        # invalid token
        r3 = requests.post(f"{API}/auth/reset-password",
                           json={"token": "bogus_" + uuid.uuid4().hex, "new_password": "another123"})
        assert r3.status_code == 400


# ---------- recipes ----------
class TestRecipes:
    def test_samples_public(self):
        r = requests.get(f"{API}/recipes/samples")
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list) and len(arr) == 3
        for s in arr:
            assert s["is_sample"] is True

    def test_demo_profiles_and_recipes(self, demo_token):
        rp = requests.get(f"{API}/profiles", headers=hdr(demo_token))
        assert rp.status_code == 200
        assert len(rp.json()) == 4
        ra = requests.get(f"{API}/recipes?tier=adult", headers=hdr(demo_token))
        assert ra.status_code == 200
        recs = ra.json()
        assert all(r["tier"] == "adult" for r in recs)
        # full recipe
        if recs:
            g = requests.get(f"{API}/recipes/{recs[0]['id']}", headers=hdr(demo_token))
            assert g.status_code == 200
            assert g.json()["title"]

    def test_non_member_this_week_402(self):
        email = f"TEST_nm_{uuid.uuid4().hex[:8]}@ex.com"
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "abcdefgh1", "family_name": "NM"})
        tok = r.json()["token"]
        rw = requests.get(f"{API}/recipes/this-week", headers=hdr(tok))
        assert rw.status_code == 402

    def test_admin_can_crud_recipe_family_cannot(self, admin_token, demo_token):
        body = {"title": "TEST Recipe", "tier": "adult", "description": "d",
                "ingredients": ["a"], "steps": ["b"]}
        # family forbidden
        rf = requests.post(f"{API}/recipes", json=body, headers=hdr(demo_token))
        assert rf.status_code == 403
        # admin ok
        ra = requests.post(f"{API}/recipes", json=body, headers=hdr(admin_token))
        assert ra.status_code == 200, ra.text
        rid = ra.json()["id"]
        # delete family forbidden
        df = requests.delete(f"{API}/recipes/{rid}", headers=hdr(demo_token))
        assert df.status_code == 403
        # admin delete
        da = requests.delete(f"{API}/recipes/{rid}", headers=hdr(admin_token))
        assert da.status_code == 200


# ---------- redeem ----------
class TestRedeem:
    def test_admin_generate_and_family_redeem(self, admin_token):
        gr = requests.post(f"{API}/admin/codes",
                           json={"duration": "monthly", "count": 1, "note": "test"},
                           headers=hdr(admin_token))
        assert gr.status_code == 200
        code = gr.json()[0]["code"]
        # new family
        email = f"TEST_rd_{uuid.uuid4().hex[:8]}@ex.com"
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "abcdefgh1", "family_name": "RD"})
        tok = r.json()["token"]
        rr = requests.post(f"{API}/redeem", json={"code": code}, headers=hdr(tok))
        assert rr.status_code == 200
        exp = rr.json()["membership_expires_at"]
        assert exp
        # verify /this-week now works
        rw = requests.get(f"{API}/recipes/this-week", headers=hdr(tok))
        assert rw.status_code == 200


# ---------- admin export ----------
class TestAdminExport:
    ENTITIES = ["families", "parents", "profiles", "recipes", "entitlements", "codes", "subscriptions"]

    @pytest.mark.parametrize("entity", ENTITIES)
    def test_csv(self, admin_token, entity):
        r = requests.get(f"{API}/admin/export/{entity}?format=csv", headers=hdr(admin_token))
        assert r.status_code == 200, f"{entity}: {r.status_code} {r.text[:200]}"
        assert "text/csv" in r.headers.get("content-type", "")

    @pytest.mark.parametrize("entity", ENTITIES)
    def test_json(self, admin_token, entity):
        r = requests.get(f"{API}/admin/export/{entity}?format=json", headers=hdr(admin_token))
        assert r.status_code == 200
        assert "application/json" in r.headers.get("content-type", "")


# ---------- flags gating ----------
class TestFlagGating:
    def test_pdf_export_gated_by_flag(self, admin_token, demo_token):
        # get demo profile
        profs = requests.get(f"{API}/profiles", headers=hdr(demo_token)).json()
        pid = profs[0]["id"]
        # default off -> 403
        r_off = requests.get(f"{API}/journal/{pid}/export", headers=hdr(demo_token))
        assert r_off.status_code == 403
        # flip on
        flags = requests.get(f"{API}/flags").json()
        flags["personalized_pdf_export"] = True
        u = requests.put(f"{API}/admin/flags", json={"flags": flags}, headers=hdr(admin_token))
        assert u.status_code == 200
        try:
            r_on = requests.get(f"{API}/journal/{pid}/export", headers=hdr(demo_token))
            assert r_on.status_code == 200
            assert r_on.headers.get("content-type", "").startswith("application/pdf")
        finally:
            flags["personalized_pdf_export"] = False
            requests.put(f"{API}/admin/flags", json={"flags": flags}, headers=hdr(admin_token))
        # after flip back
        r_back = requests.get(f"{API}/journal/{pid}/export", headers=hdr(demo_token))
        assert r_back.status_code == 403

    def test_kid_photo_upload_blocked(self, demo_token):
        files = {"file": ("t.png", b"fakepng", "image/png")}
        data = {"purpose": "child_photo"}
        r = requests.post(f"{API}/files/upload", files=files, data=data, headers=hdr(demo_token))
        assert r.status_code == 403


# ---------- stripe / pricing ----------
class TestPayments:
    def test_pricing_returns_4_tiers(self):
        r = requests.get(f"{API}/payments/pricing")
        assert r.status_code == 200
        arr = r.json()
        keys = {p["lookup_key"] for p in arr}
        assert keys == {"monthly", "3month", "6month", "annual"}

    def test_checkout_returns_stripe_url(self, demo_token):
        r = requests.post(f"{API}/payments/checkout",
                          json={"lookup_key": "monthly", "origin_url": BASE},
                          headers=hdr(demo_token))
        assert r.status_code == 200, r.text
        url = r.json()["checkout_url"]
        assert "stripe.com" in url or "checkout.stripe" in url


# ---------- branding logo ----------
class TestLogo:
    def test_upload_and_fetch_logo(self, admin_token):
        # make a tiny valid PNG (1x1) using minimal bytes
        png = (b"\x89PNG\r\n\x1a\n"
               b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
               b"\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x5b\xdb\x8b\xe0"
               b"\x00\x00\x00\x00IEND\xaeB`\x82")
        files = {"file": ("logo.png", png, "image/png")}
        r = requests.put(f"{API}/admin/branding/logo", files=files, headers=hdr(admin_token))
        # some servers use POST; API defines POST. Try both.
        if r.status_code == 405:
            r = requests.post(f"{API}/admin/branding/logo", files=files, headers=hdr(admin_token))
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        fid = r.json().get("file_id")
        assert fid
        g = requests.get(f"{API}/branding/logo")
        assert g.status_code == 200 and g.json().get("file_id") == fid
        raw = requests.get(f"{API}/branding/logo/raw")
        assert raw.status_code == 200
        assert raw.headers.get("content-type", "").startswith("image/")
