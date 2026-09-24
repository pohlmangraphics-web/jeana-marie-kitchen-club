"""Iteration 18: verify 5 new launch recipes read-only.
Read-only: does not create/modify anything. No emails, no Stripe."""
import os
import re
import io
import requests
import pytest
from pypdf import PdfReader

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(__file__)); from creds import DEMO, ADMIN  # noqa: E402

LAUNCH = [
    ("Mini Rainbow Pizza Bites", "little"),
    ("Chocolate Chip Cookie Shop Cookies", "junior"),
    ("Kid-Friendly Walking Tacos", "junior"),
    ("Dunkable Grilled Cheese & Tomato Soup", "young"),
    ("Ultimate Smash Burgers", "teen"),
]

TIER_LABEL = {
    "little": "LITTLE CHEFS (AGES 3-5)",
    "junior": "JUNIOR COOKS (AGES 6-9)",
    "young": "YOUNG CHEFS (AGES 10-12)",
    "teen": "TEEN KITCHEN (AGES 13-15+)",
}


@pytest.fixture(scope="module")
def demo_token():
    r = requests.post(f"{BASE}/api/auth/login", json=DEMO, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def demo_headers(demo_token):
    return {"Authorization": f"Bearer {demo_token}"}


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def all_recipes(demo_headers):
    r = requests.get(f"{BASE}/api/recipes", headers=demo_headers, timeout=30)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(scope="module")
def by_title(all_recipes):
    m = {}
    for r in all_recipes:
        m.setdefault(r["title"], []).append(r)
    return m


def test_recipes_total_count(all_recipes):
    assert len(all_recipes) == 12, f"expected 12 recipes, got {len(all_recipes)}"


def test_each_launch_title_unique(by_title):
    for title, _ in LAUNCH:
        assert title in by_title, f"missing {title}"
        assert len(by_title[title]) == 1, f"duplicate {title}"


def test_launch_tiers_and_fields(by_title):
    for title, tier in LAUNCH:
        r = by_title[title][0]
        assert r["tier"] == tier, f"{title} tier {r['tier']}!={tier}"
        assert r.get("is_sample") in (False, None), f"{title} is_sample={r.get('is_sample')}"
        assert r.get("safety_notes"), f"{title} missing safety_notes"
        assert isinstance(r["safety_notes"], list) and len(r["safety_notes"]) > 0
        assert r.get("time_text"), f"{title} missing time_text"


def test_tips_required():
    pass  # placeholder — done below


def test_cookies_and_burgers_tips(by_title):
    for t in ("Chocolate Chip Cookie Shop Cookies", "Ultimate Smash Burgers"):
        tips = by_title[t][0].get("tips")
        assert tips and len(tips) > 0, f"{t} tips missing"


def test_yield_text_required(by_title):
    for t in ("Mini Rainbow Pizza Bites", "Chocolate Chip Cookie Shop Cookies", "Ultimate Smash Burgers"):
        assert by_title[t][0].get("yield_text"), f"{t} yield_text missing"


@pytest.mark.parametrize("tier,included,excluded", [
    ("little", ["Mini Rainbow Pizza Bites"], ["Chocolate Chip Cookie Shop Cookies", "Kid-Friendly Walking Tacos", "Dunkable Grilled Cheese & Tomato Soup", "Ultimate Smash Burgers"]),
    ("junior", ["Chocolate Chip Cookie Shop Cookies", "Kid-Friendly Walking Tacos"], ["Mini Rainbow Pizza Bites", "Dunkable Grilled Cheese & Tomato Soup", "Ultimate Smash Burgers"]),
    ("young", ["Dunkable Grilled Cheese & Tomato Soup"], ["Mini Rainbow Pizza Bites", "Chocolate Chip Cookie Shop Cookies", "Kid-Friendly Walking Tacos", "Ultimate Smash Burgers"]),
    ("teen", ["Ultimate Smash Burgers"], ["Mini Rainbow Pizza Bites", "Chocolate Chip Cookie Shop Cookies", "Kid-Friendly Walking Tacos", "Dunkable Grilled Cheese & Tomato Soup"]),
    ("family", [], [t for t, _ in LAUNCH]),
])
def test_tier_filter(demo_headers, tier, included, excluded):
    r = requests.get(f"{BASE}/api/recipes", params={"tier": tier}, headers=demo_headers, timeout=30)
    assert r.status_code == 200
    titles = {x["title"] for x in r.json()}
    for t in included:
        assert t in titles, f"tier={tier} missing {t}"
        for t in excluded:
            pass
    for t in excluded:
        assert t not in titles, f"tier={tier} should not contain {t}"


def test_recipe_get_and_card(demo_headers, by_title):
    for title, tier in LAUNCH:
        rid = by_title[title][0]["id"]
        # GET single
        r = requests.get(f"{BASE}/api/recipes/{rid}", headers=demo_headers, timeout=30)
        assert r.status_code == 200, f"{title} GET failed: {r.status_code}"
        # GET card
        c = requests.get(f"{BASE}/api/recipes/{rid}/card", headers=demo_headers, timeout=60)
        assert c.status_code == 200, f"{title} card status {c.status_code}"
        assert c.headers.get("content-type", "").startswith("application/pdf")
        assert c.headers.get("X-Recipe-Card-Source") == "generated"
        pdf = PdfReader(io.BytesIO(c.content))
        assert len(pdf.pages) >= 1
        full = ""
        for p in pdf.pages:
            t = p.extract_text() or ""
            assert t.strip(), f"{title} blank page"
            full += "\n" + t
        norm = re.sub(r"\s+", " ", full)
        assert "Kitchen Club" in full or "Kitchen Club" in norm
        assert re.search(r"safety\s*&?\s*adult\s*help", full, re.IGNORECASE), f"{title} missing SAFETY & ADULT HELP"
        assert re.search(r"learning\s*activity", full, re.IGNORECASE), f"{title} missing LEARNING ACTIVITY"
        assert "Private Chef" not in full, f"{title} contains Private Chef"
        for old in ("Ages 4–6", "Ages 8–11", "Ages 12–15"):
            assert old not in full, f"{title} contains old age label {old}"
        # Tier label match tolerant of whitespace
        label = TIER_LABEL[tier]
        pattern = r"\s*".join(re.escape(ch) for ch in label)
        assert re.search(pattern, full, re.IGNORECASE) or re.search(pattern, norm, re.IGNORECASE), \
            f"{title} missing tier label {label}"


def test_card_requires_auth(by_title):
    rid = by_title["Ultimate Smash Burgers"][0]["id"]
    r = requests.get(f"{BASE}/api/recipes/{rid}/card", timeout=30)
    assert r.status_code == 401, f"expected 401, got {r.status_code}"


def test_photo_urls_public(by_title):
    with_photo = 0
    for title, _ in LAUNCH:
        rec = by_title[title][0]
        photo_url = rec.get("photo_url")
        if not photo_url or "/api/files/" not in photo_url:
            continue
        with_photo += 1
        url = photo_url if photo_url.startswith("http") else BASE + photo_url
        r = requests.get(url, timeout=60)
        assert r.status_code == 200, f"{title} photo {url} -> {r.status_code}"
        assert r.headers.get("content-type", "").startswith("image/jpeg"), f"{title} content-type {r.headers.get('content-type')}"
        assert len(r.content) > 10_000, f"{title} photo too small {len(r.content)}"
    assert with_photo == 4, f"expected 4 recipes with /api/files photo_url, got {with_photo}"


def test_non_photo_file_requires_auth():
    r = requests.get(f"{BASE}/api/files/7be730c8-6391-4bc2-a27c-a8b2249b8ad2", timeout=30)
    assert r.status_code == 401, f"expected 401 for non-photo file, got {r.status_code}"


def test_featured_recipe_unchanged(demo_headers):
    r = requests.get(f"{BASE}/api/recipes/featured", headers=demo_headers, timeout=30)
    assert r.status_code == 200
    data = r.json()
    rec = data.get("recipe", data)
    assert rec["id"] == "502ef474-b8a0-4f5e-8188-d09af0fd0bce", f"featured id={rec.get('id')}"
    assert rec["title"] == "Rainbow Fruit Kabobs"


def test_admin_printables_count(admin_headers):
    r = requests.get(f"{BASE}/api/printables", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    lst = r.json()
    assert len(lst) == 5, f"admin printables={len(lst)}"
    hidden = sum(1 for p in lst if p.get("is_hidden"))
    assert hidden == 3, f"is_hidden count={hidden}"
