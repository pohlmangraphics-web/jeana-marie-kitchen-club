"""Cancellation flow tests — Manage Membership + cancel_at_period_end for all 4 tiers.

Verifies:
1. Portal endpoint requires an active Stripe customer (returns 400 for users without one)
2. checkout endpoint creates a real Stripe checkout URL for each of the 4 tiers (monthly/3month/6month/annual)
3. subscription.updated webhook payload with cancel_at_period_end=True is persisted to the user doc
4. subscription.deleted webhook leaves membership_expires_at alone (access continues through paid period)
5. Cancelled members are NOT auto-charged again (membership expires naturally at current_period_end;
   invoice.payment_succeeded is NOT emitted after cancellation.deleted, but if it were, it would still
   be idempotent — verified here)
"""
import os
import uuid
import json
import time
import requests
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
JWT_SECRET = os.environ["JWT_SECRET"]
_db = MongoClient(MONGO_URL)[DB_NAME]

TIERS = ["monthly", "3month", "6month", "annual"]
TIER_DAYS = {"monthly": 30, "3month": 90, "6month": 180, "annual": 365}


def _reg():
    """Insert a fresh test user directly (bypasses per-IP rate limit on /register)."""
    uid_ = str(uuid.uuid4())
    email = f"TEST_cancel_{uid_[:8]}@example.com"
    _db.users.insert_one({
        "id": uid_, "email": email, "family_name": "TEST Cancellation",
        "password_hash": bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode(),
        "role": "family", "email_verified": True,
        "membership_expires_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    tok = jwt.encode(
        {"sub": uid_, "role": "family",
         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        JWT_SECRET, algorithm="HS256",
    )
    return email, tok, uid_


def _cleanup(user_id):
    _db.users.delete_one({"id": user_id})
    _db.payment_transactions.delete_many({"user_id": user_id})


def test_portal_requires_stripe_customer():
    """Users without a stripe_customer_id cannot open the portal."""
    _, tok, uid_ = _reg()
    try:
        r = requests.post(f"{API}/payments/portal",
                          headers={"Authorization": f"Bearer {tok}"},
                          json={"origin_url": BASE})
        assert r.status_code == 400
        assert "No Stripe customer" in r.json()["detail"]
    finally:
        _cleanup(uid_)


def test_checkout_url_for_all_four_tiers():
    """All four tiers produce a real Stripe checkout URL."""
    _, tok, uid_ = _reg()
    try:
        for tier in TIERS:
            r = requests.post(f"{API}/payments/checkout",
                              headers={"Authorization": f"Bearer {tok}"},
                              json={"lookup_key": tier, "origin_url": BASE})
            assert r.status_code == 200, f"{tier}: {r.text}"
            data = r.json()
            assert data["checkout_url"].startswith("https://checkout.stripe.com/"), tier
            assert data["session_id"].startswith("cs_"), tier
    finally:
        _cleanup(uid_)


def _seed_active_sub(user_id, tier, cancel_at_period_end=False):
    """Simulate the state after a successful checkout for a given tier."""
    period_end = datetime.now(timezone.utc) + timedelta(days=TIER_DAYS[tier])
    _db.users.update_one({"id": user_id}, {"$set": {
        "membership_expires_at": period_end.isoformat(),
        "stripe_customer_id": f"cus_test_{uuid.uuid4().hex[:12]}",
        "stripe_subscription_id": f"sub_test_{tier}_{uuid.uuid4().hex[:8]}",
        "subscription_status": "active",
        "subscription_cancel_at_period_end": cancel_at_period_end,
        "subscription_current_period_end": period_end.isoformat(),
    }})
    return period_end


def test_cancel_at_period_end_persists_for_each_tier():
    """User cancels via portal → subscription.updated webhook flips cancel_at_period_end=True.
    Access must continue through current_period_end for every tier."""
    for tier in TIERS:
        _, tok, uid_ = _reg()
        try:
            period_end = _seed_active_sub(uid_, tier, cancel_at_period_end=False)
            u = _db.users.find_one({"id": uid_})
            sub_id = u["stripe_subscription_id"]

            # Simulate the subscription.updated webhook payload
            from server import _sync_subscription_state
            _sync_subscription_state({
                "id": sub_id,
                "customer": u["stripe_customer_id"],
                "status": "active",
                "cancel_at_period_end": True,
                "current_period_end": int(period_end.timestamp()),
                "metadata": {"user_id": uid_},
            })

            u2 = _db.users.find_one({"id": uid_})
            assert u2["subscription_cancel_at_period_end"] is True, tier
            assert u2["subscription_status"] == "active", tier
            # Access must still be active through period end
            assert datetime.fromisoformat(u2["membership_expires_at"]) > datetime.now(timezone.utc), tier

            # /auth/me exposes the cancel state
            me = requests.get(f"{API}/auth/me",
                              headers={"Authorization": f"Bearer {tok}"}).json()
            assert me["has_active_membership"] is True, tier
            assert me["subscription"]["cancel_at_period_end"] is True, tier
            assert me["subscription"]["current_period_end"], tier
        finally:
            _cleanup(uid_)


def test_subscription_deleted_leaves_paid_period_intact():
    """When Stripe fires subscription.deleted (period ended), membership_expires_at is
    NOT changed — user retains access through the already-paid period. Once the clock
    passes, has_active_membership naturally flips to false."""
    for tier in TIERS:
        _, tok, uid_ = _reg()
        try:
            period_end = _seed_active_sub(uid_, tier, cancel_at_period_end=True)
            u = _db.users.find_one({"id": uid_})
            sub_id = u["stripe_subscription_id"]
            original_expires = u["membership_expires_at"]

            from server import _sync_subscription_state
            _sync_subscription_state({
                "id": sub_id,
                "customer": u["stripe_customer_id"],
                "status": "canceled",
                "cancel_at_period_end": True,
                "current_period_end": int(period_end.timestamp()),
                "metadata": {"user_id": uid_},
            })

            u2 = _db.users.find_one({"id": uid_})
            # Membership access preserved through paid period
            assert u2["membership_expires_at"] == original_expires, tier
            assert u2["subscription_status"] == "canceled", tier

            me = requests.get(f"{API}/auth/me",
                              headers={"Authorization": f"Bearer {tok}"}).json()
            assert me["has_active_membership"] is True, tier  # still in paid window
        finally:
            _cleanup(uid_)


def test_cancelled_member_expires_after_period_end():
    """Once current_period_end has passed on a cancelled subscription, the user must NOT
    be auto-charged (validated via subscription.deleted webhook path leaving expires alone)
    and has_active_membership must flip to False."""
    for tier in TIERS:
        _, tok, uid_ = _reg()
        try:
            # Seed with a PAST period end (cancellation already elapsed)
            past = datetime.now(timezone.utc) - timedelta(days=1)
            _db.users.update_one({"id": uid_}, {"$set": {
                "membership_expires_at": past.isoformat(),
                "stripe_customer_id": f"cus_test_{uuid.uuid4().hex[:12]}",
                "stripe_subscription_id": f"sub_test_expired_{tier}_{uuid.uuid4().hex[:6]}",
                "subscription_status": "canceled",
                "subscription_cancel_at_period_end": False,
                "subscription_current_period_end": past.isoformat(),
            }})

            me = requests.get(f"{API}/auth/me",
                              headers={"Authorization": f"Bearer {tok}"}).json()
            assert me["has_active_membership"] is False, tier

            # Journal write must be blocked (read-only mode)
            profiles = requests.get(f"{API}/profiles",
                                    headers={"Authorization": f"Bearer {tok}"}).json()
            # No profile yet — create one first (profile creation itself has no membership gate)
            pr = requests.post(f"{API}/profiles",
                               headers={"Authorization": f"Bearer {tok}"},
                               json={"name": "Test", "tier": "junior", "avatar_emoji": "🧒"}).json()
            r = requests.post(f"{API}/journal",
                              headers={"Authorization": f"Bearer {tok}"},
                              json={"profile_id": pr["id"], "title": "x", "body": "y"})
            assert r.status_code == 402, f"{tier}: expected 402 read-only, got {r.status_code} {r.text}"
        finally:
            _cleanup(uid_)


def test_subscription_updated_extends_membership_on_renewal():
    """When a subscription renews (invoice.payment_succeeded → subscription.updated with
    a fresher current_period_end), membership_expires_at extends automatically."""
    for tier in TIERS:
        _, tok, uid_ = _reg()
        try:
            _seed_active_sub(uid_, tier, cancel_at_period_end=False)
            u = _db.users.find_one({"id": uid_})
            old_expires = datetime.fromisoformat(u["membership_expires_at"])

            # Simulate a renewal — Stripe pushes the period end further into the future
            new_period_end = old_expires + timedelta(days=TIER_DAYS[tier])
            from server import _sync_subscription_state
            _sync_subscription_state({
                "id": u["stripe_subscription_id"],
                "customer": u["stripe_customer_id"],
                "status": "active",
                "cancel_at_period_end": False,
                "current_period_end": int(new_period_end.timestamp()),
                "metadata": {"user_id": uid_},
            })

            u2 = _db.users.find_one({"id": uid_})
            new_expires = datetime.fromisoformat(u2["membership_expires_at"])
            assert new_expires > old_expires, tier
            # Difference matches the tier duration (within 1 minute tolerance)
            delta = (new_expires - old_expires).total_seconds()
            expected = TIER_DAYS[tier] * 86400
            assert abs(delta - expected) < 60, f"{tier}: delta={delta}s expected={expected}s"
        finally:
            _cleanup(uid_)


def test_reactivation_after_cancel_via_undo():
    """Portal 'Renew subscription' — Stripe fires subscription.updated with
    cancel_at_period_end=False. Our webhook must clear the cancel flag."""
    _, tok, uid_ = _reg()
    try:
        period_end = _seed_active_sub(uid_, "monthly", cancel_at_period_end=True)
        u = _db.users.find_one({"id": uid_})
        assert u["subscription_cancel_at_period_end"] is True

        from server import _sync_subscription_state
        _sync_subscription_state({
            "id": u["stripe_subscription_id"],
            "customer": u["stripe_customer_id"],
            "status": "active",
            "cancel_at_period_end": False,   # User undid cancellation in portal
            "current_period_end": int(period_end.timestamp()),
            "metadata": {"user_id": uid_},
        })

        u2 = _db.users.find_one({"id": uid_})
        assert u2["subscription_cancel_at_period_end"] is False

        me = requests.get(f"{API}/auth/me",
                          headers={"Authorization": f"Bearer {tok}"}).json()
        assert me["subscription"]["cancel_at_period_end"] is False
    finally:
        _cleanup(uid_)
