"""Iteration 10 tests: recipe categories + admin-configurable Etsy shop URL."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://recipe-journal-club.preview.emergentagent.com').rstrip('/')

ADMIN_EMAIL = "admin@jeanamarie.club"
ADMIN_PASS = "JeanaAdmin2026!"
FAMILY_EMAIL = "demo@family.com"
FAMILY_PASS = "DemoFamily123!"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN_EMAIL, ADMIN_PASS)}"}


@pytest.fixture(scope="module")
def family_headers():
    return {"Authorization": f"Bearer {_login(FAMILY_EMAIL, FAMILY_PASS)}"}


@pytest.fixture(scope="module")
def created_recipe_ids():
    return []


# --- Categories tests ---

def test_create_recipe_with_categories(admin_headers, created_recipe_ids):
    body = {
        "title": "TEST_ITER10_Breakfast_Snack",
        "tier": "adult",
        "description": "iter10 test",
        "ingredients": ["a", "b"],
        "steps": ["1", "2"],
        "categories": ["Breakfast", "Snack"],
    }
    r = requests.post(f"{BASE_URL}/api/recipes", json=body, headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["categories"] == ["Breakfast", "Snack"]
    created_recipe_ids.append(data["id"])


def test_create_recipe_without_categories_defaults_empty(admin_headers, created_recipe_ids):
    body = {
        "title": "TEST_ITER10_NoCats",
        "tier": "adult",
        "description": "iter10 test",
        "ingredients": ["a"],
        "steps": ["1"],
    }
    r = requests.post(f"{BASE_URL}/api/recipes", json=body, headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["categories"] == []
    created_recipe_ids.append(data["id"])


def test_patch_recipe_categories(admin_headers, created_recipe_ids):
    rid = created_recipe_ids[1]
    r = requests.patch(f"{BASE_URL}/api/recipes/{rid}", json={"categories": ["Dinner"]}, headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["categories"] == ["Dinner"]
    # Verify GET returns the array
    r2 = requests.get(f"{BASE_URL}/api/recipes/{rid}", headers=admin_headers, timeout=30)
    assert r2.status_code == 200
    assert r2.json()["categories"] == ["Dinner"]


def test_get_recipes_filter_by_category(admin_headers, created_recipe_ids):
    # Filter by Breakfast should include first recipe
    r = requests.get(f"{BASE_URL}/api/recipes?category=Breakfast", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert created_recipe_ids[0] in ids
    assert created_recipe_ids[1] not in ids
    for rec in r.json():
        assert "Breakfast" in (rec.get("categories") or [])


def test_get_recipes_filter_empty_when_no_match(admin_headers):
    r = requests.get(f"{BASE_URL}/api/recipes?category=NoSuchCategoryXYZ", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    assert r.json() == []


def test_get_recipes_combined_tier_and_category(admin_headers, created_recipe_ids):
    r = requests.get(f"{BASE_URL}/api/recipes?tier=adult&category=Dinner", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert created_recipe_ids[1] in ids
    for rec in r.json():
        assert rec["tier"] == "adult"
        assert "Dinner" in (rec.get("categories") or [])


# --- Etsy URL tests ---

def test_etsy_url_public_no_auth():
    r = requests.get(f"{BASE_URL}/api/branding/etsy-url", timeout=30)
    assert r.status_code == 200
    assert "url" in r.json()


def test_etsy_url_admin_set_and_get(admin_headers):
    test_url = "https://www.etsy.com/shop/TESTITER10Shop"
    r = requests.put(f"{BASE_URL}/api/admin/branding/etsy-url", json={"url": test_url}, headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["url"] == test_url
    # verify public GET reflects it
    r2 = requests.get(f"{BASE_URL}/api/branding/etsy-url", timeout=30)
    assert r2.json()["url"] == test_url


def test_etsy_url_family_forbidden(family_headers):
    r = requests.put(f"{BASE_URL}/api/admin/branding/etsy-url", json={"url": "https://x.com"}, headers=family_headers, timeout=30)
    assert r.status_code == 403


def test_etsy_url_clear(admin_headers):
    r = requests.put(f"{BASE_URL}/api/admin/branding/etsy-url", json={"url": ""}, headers=admin_headers, timeout=30)
    assert r.status_code == 200
    assert r.json()["url"] == ""
    r2 = requests.get(f"{BASE_URL}/api/branding/etsy-url", timeout=30)
    assert r2.json()["url"] == ""


# --- Regression ---

def test_regression_endpoints(admin_headers, family_headers):
    endpoints = [
        ("GET", "/api/", None),
        ("GET", "/api/recipes/samples", None),
        ("GET", "/api/recipes", family_headers),
        ("GET", "/api/printables", family_headers),
        ("GET", "/api/recipes/featured", family_headers),
        ("GET", "/api/admin/codes", admin_headers),
        ("GET", "/api/flags", None),
    ]
    for method, path, headers in endpoints:
        r = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=30)
        assert r.status_code == 200, f"{method} {path} -> {r.status_code}"


# --- Cleanup ---

def test_cleanup(admin_headers, created_recipe_ids):
    for rid in created_recipe_ids:
        requests.delete(f"{BASE_URL}/api/recipes/{rid}", headers=admin_headers, timeout=30)
