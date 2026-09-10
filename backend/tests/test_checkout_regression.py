"""Iteration 13 — Checkout-flow regression (backend portions of scenarios 4 & 7)."""
import os
import uuid
import time
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
_db = MongoClient(MONGO_URL)[DB_NAME]


def _reg(email=None, pw="TestPass123!", family="TEST Regression"):
    email = email or f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": pw, "family_name": family
    })
    assert r.status_code == 200, r.text
    return email, pw, r.json()["token"]


# -------- Scenario 4: successful checkout via DB mutation + status polling --------
def test_scenario4_checkout_and_grant_flow():
    email, pw, tok = _reg()
    h = {"Authorization": f"Bearer {tok}"}

    # /api/auth/me: fresh user has no membership
    me = requests.get(f"{API}/auth/me", headers=h).json()
    assert me["has_active_membership"] is False, me

    # POST /api/payments/checkout for monthly
    r = requests.post(f"{API}/payments/checkout", headers=h,
                      json={"lookup_key": "monthly", "origin_url": BASE})
    assert r.status_code == 200, r.text
    body = r.json()
    session_id = body["session_id"]
    assert body["checkout_url"].startswith("https://checkout.stripe.com/"), body["checkout_url"]

    # Verify payment_transactions doc exists with status=initiated
    tx = _db.payment_transactions.find_one({"session_id": session_id})
    assert tx is not None
    assert tx["status"] == "initiated"
    assert tx["payment_status"] == "pending"
    assert tx["user_id"] == me["id"]
    assert tx["lookup_key"] == "monthly"

    # Simulate paid webhook via direct DB write + grant membership
    _db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed", "payment_status": "paid",
                  "updated_at": datetime.now(timezone.utc)}},
    )
    # Grant membership by mimicking _grant_membership (monthly = ~30 days)
    new_exp = datetime.now(timezone.utc) + timedelta(days=30)
    _db.users.update_one({"id": me["id"]},
                         {"$set": {"membership_expires_at": new_exp.isoformat()}})

    # /api/auth/me now shows active membership
    me2 = requests.get(f"{API}/auth/me", headers=h).json()
    assert me2["has_active_membership"] is True, me2

    # /api/payments/status/{sid} returns paid
    st = requests.get(f"{API}/payments/status/{session_id}").json()
    assert st["payment_status"] == "paid", st
    assert st["status"] == "completed", st


# -------- Scenario 7: password reset token single-use --------
def test_scenario7_reset_token_single_use():
    email, pw, tok = _reg(pw="OldPass123!")
    # Forgot password
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": True}, body

    # Fetch reset token from Mongo
    u = _db.users.find_one({"email": email.lower()})
    reset_token = u.get("reset_token") if u else None
    assert reset_token, f"no reset_token in db for {email}"

    # First reset -> success
    new_pw = "NewPass456!"
    r1 = requests.post(f"{API}/auth/reset-password",
                       json={"token": reset_token, "new_password": new_pw})
    assert r1.status_code == 200, r1.text

    # Second reset with same token -> 400 Invalid or expired token
    r2 = requests.post(f"{API}/auth/reset-password",
                       json={"token": reset_token, "new_password": "Another789!"})
    assert r2.status_code == 400, r2.text
    assert "invalid" in r2.json().get("detail", "").lower() or "expired" in r2.json().get("detail", "").lower()

    # Old password no longer works
    r_old = requests.post(f"{API}/auth/login", json={"email": email, "password": "OldPass123!"})
    assert r_old.status_code == 401, r_old.text

    # New password works
    r_new = requests.post(f"{API}/auth/login", json={"email": email, "password": new_pw})
    assert r_new.status_code == 200, r_new.text


# -------- Additional sanity: signed-in-unpaid can hit checkout without register --------
def test_signed_in_unpaid_can_reach_stripe_directly():
    email, pw, tok = _reg()
    h = {"Authorization": f"Bearer {tok}"}
    for plan in ["monthly", "3month", "6month", "annual"]:
        r = requests.post(f"{API}/payments/checkout", headers=h,
                          json={"lookup_key": plan, "origin_url": BASE})
        assert r.status_code == 200, f"{plan}: {r.text}"
        url = r.json()["checkout_url"]
        assert url.startswith("https://checkout.stripe.com/"), f"{plan}: {url}"
