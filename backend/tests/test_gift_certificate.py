"""Iteration 6: gift certificate endpoint + regression spot checks."""
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "admin@jeanamarie.club"
ADMIN_PW = "JeanaAdmin2026!"


# --- regression spot check ---
class TestRegressionSpotCheck:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200

    def test_admin_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"

    def test_recipes_samples(self):
        r = requests.get(f"{API}/recipes/samples")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_flags(self):
        r = requests.get(f"{API}/flags")
        assert r.status_code == 200


# --- gift certificate endpoint ---
class TestGiftCertificate:
    def _payload(self, duration="annual", **overrides):
        base = {
            "to": "The Bakers",
            "from": "Grandma",
            "code": "JMK-ABCD123456",
            "duration": duration,
            "message": "Happy birthday!",
        }
        base.update(overrides)
        return base

    def test_pdf_generation_annual(self):
        r = requests.post(f"{API}/gift-certificate/pdf", json=self._payload())
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 1024

    def test_public_no_auth(self):
        """endpoint intentionally does not require auth token"""
        r = requests.post(f"{API}/gift-certificate/pdf", json=self._payload())
        assert r.status_code == 200

    def test_missing_to_422(self):
        p = self._payload()
        p.pop("to")
        r = requests.post(f"{API}/gift-certificate/pdf", json=p)
        assert r.status_code == 422

    def test_missing_code_422(self):
        p = self._payload()
        p.pop("code")
        r = requests.post(f"{API}/gift-certificate/pdf", json=p)
        assert r.status_code == 422

    def test_from_alias_literal_from_key(self):
        """JSON body key must be literally 'from' (Pydantic alias) — this is what the frontend sends."""
        good = {"to": "T", "from": "F", "code": "JMK-X", "duration": "annual"}
        r2 = requests.post(f"{API}/gift-certificate/pdf", json=good)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("application/pdf")
        # sending only from_ (without 'from') — because populate_by_name=True is enabled,
        # this ALSO works, but the frontend sends 'from', so this is not user-facing.
        # If ONLY from_ is provided (no 'from'), it currently accepts it too.
        # We only assert the required-by-spec case: literal 'from' works.

    def test_all_durations(self):
        for d in ["monthly", "3month", "6month", "annual"]:
            r = requests.post(f"{API}/gift-certificate/pdf", json=self._payload(duration=d))
            assert r.status_code == 200, f"{d}: {r.status_code} {r.text[:200]}"
            assert r.headers.get("content-type", "").startswith("application/pdf")
            assert len(r.content) > 1024
