"""Password-reset flow: valid reset, invalid/expired/used token, and 422 error shape.
Tokens are injected via DB so no email is sent."""
import os
import uuid
import secrets
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _user(pw="OldPass123!"):
    email = f"test_reset_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": pw, "family_name": "TEST Reset"})
    assert r.status_code == 200, r.text
    return email


def _inject_token(email, hours=1):
    tok = secrets.token_urlsafe(32)
    _db.users.update_one({"email": email}, {"$set": {
        "reset_token": tok,
        "reset_token_expires": (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()}})
    return tok


def _login(email, pw):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": pw}).status_code


def test_valid_reset_succeeds_and_token_single_use():
    email = _user()
    tok = _inject_token(email)
    r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": "NewPass456!"})
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert _login(email, "NewPass456!") == 200
    assert _login(email, "OldPass123!") in (400, 401)
    r2 = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": "Another789!"})
    assert r2.status_code == 400 and r2.json()["detail"] == "Invalid or expired token"
    assert _db.users.find_one({"email": email}).get("reset_token") is None


def test_invalid_token_is_friendly_string():
    r = requests.post(f"{API}/auth/reset-password", json={"token": "nope-" + uuid.uuid4().hex, "new_password": "NewPass456!"})
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str)


def test_expired_token_rejected():
    email = _user()
    tok = _inject_token(email, hours=-1)
    r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": "NewPass456!"})
    assert r.status_code == 400 and r.json()["detail"] == "Token expired"
    assert _login(email, "OldPass123!") == 200


def test_short_password_returns_422_array_shape():
    """Documents the exact shape that previously crashed React; frontend errorMessage() must flatten it."""
    email = _user()
    tok = _inject_token(email)
    r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "new_password": "short"})
    assert r.status_code == 422
    d = r.json()["detail"]
    assert isinstance(d, list) and d[0]["loc"][-1] == "new_password" and d[0]["type"] == "string_too_short"
    assert _login(email, "OldPass123!") == 200  # nothing changed


def test_missing_fields_422():
    r = requests.post(f"{API}/auth/reset-password", json={"new_password": "NewPass456!"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)


def test_forgot_password_invalid_email_422_and_unknown_email_ok():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": "notanemail"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)
    r = requests.post(f"{API}/auth/forgot-password", json={"email": f"TEST_none_{uuid.uuid4().hex[:6]}@example.com"})
    assert r.status_code == 200 and r.json() == {"ok": True}  # no enumeration, no email sent
