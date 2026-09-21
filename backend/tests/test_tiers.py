"""Tier restructuring: validation, legacy 'adult' mapping, filters, profile handling, PDF/email labels. No emails sent."""
import io
import os
import sys
import uuid
import pytest
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, os.path.dirname(__file__))
from creds import ADMIN, DEMO  # noqa: E402
from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # noqa: E702
import server  # noqa: E402
import recipe_card  # noqa: E402
from pymongo import MongoClient  # noqa: E402

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
pdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def admin_h():
    r = requests.post(f"{BASE}/auth/login", json=ADMIN); assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def demo_h():
    r = requests.post(f"{BASE}/auth/login", json=DEMO); assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_normalize_tier_unit():
    assert server.normalize_tier("adult") == "family"
    assert server.normalize_tier(" Young ") == "young"
    assert server.normalize_tier(None) is None
    for t in server.TIER_KEYS: assert server.normalize_tier(t) == t
    with pytest.raises(server.HTTPException) as e: server.normalize_tier("grownups")
    assert e.value.status_code == 422
    assert server._tier_query("family") == {"$in": ["family", "adult"]} and server._tier_query("young") == "young"
    assert server._out_tier({"tier": "adult"})["tier"] == "family" and server._out_tier({"tier": "teen"})["tier"] == "teen"


def test_recipe_create_accepts_young_and_maps_adult(admin_h):
    body = {"title": f"TEST Tier Recipe {uuid.uuid4().hex[:6]}", "tier": "young", "description": "t", "ingredients": ["a"], "steps": ["b"]}
    r = requests.post(f"{BASE}/recipes", headers=admin_h, json=body); assert r.status_code == 200 and r.json()["tier"] == "young"
    rid = r.json()["id"]
    try:
        p = requests.patch(f"{BASE}/recipes/{rid}", headers=admin_h, json={"tier": "adult"}); assert p.status_code == 200
        assert pdb.recipes.find_one({"id": rid})["tier"] == "family"  # stored canonical
        assert requests.get(f"{BASE}/recipes/{rid}", headers=admin_h).json()["tier"] == "family"
        bad = requests.post(f"{BASE}/recipes", headers=admin_h, json={**body, "tier": "grownups"}); assert bad.status_code == 422
        # filters: canonical + legacy alias both resolve, unknown rejected
        ids = lambda res: {x["id"] for x in res.json()}
        assert rid in ids(requests.get(f"{BASE}/recipes?tier=family", headers=admin_h))
        assert rid in ids(requests.get(f"{BASE}/recipes?tier=adult", headers=admin_h))
        assert rid not in ids(requests.get(f"{BASE}/recipes?tier=teen", headers=admin_h))
        assert requests.get(f"{BASE}/recipes?tier=nope", headers=admin_h).status_code == 422
        # legacy stored value still surfaces as family
        pdb.recipes.update_one({"id": rid}, {"$set": {"tier": "adult"}})
        assert requests.get(f"{BASE}/recipes/{rid}", headers=admin_h).json()["tier"] == "family"
        assert rid in ids(requests.get(f"{BASE}/recipes?tier=family", headers=admin_h))
    finally:
        pdb.recipes.delete_one({"id": rid})


def test_profile_tier_validation_and_mapping(demo_h):
    r = requests.post(f"{BASE}/profiles", headers=demo_h, json={"name": "TEST Young", "tier": "young", "avatar_emoji": "🧑‍🍳"})
    if r.status_code == 400: pytest.skip("demo family at profile limit")
    assert r.status_code == 200 and r.json()["tier"] == "young"; pid = r.json()["id"]
    try:
        u = requests.patch(f"{BASE}/profiles/{pid}", headers=demo_h, json={"tier": "adult"}); assert u.status_code == 200
        assert pdb.profiles.find_one({"id": pid})["tier"] == "family"
        assert next(p for p in requests.get(f"{BASE}/profiles", headers=demo_h).json() if p["id"] == pid)["tier"] == "family"
        assert requests.post(f"{BASE}/profiles", headers=demo_h, json={"name": "x", "tier": "grownup"}).status_code == 422
    finally:
        pdb.profiles.delete_one({"id": pid})


def test_printable_tier_filter_and_alias(admin_h):
    assert requests.get(f"{BASE}/printables?tier=young", headers=admin_h).status_code == 200
    a = requests.get(f"{BASE}/printables?tier=family", headers=admin_h).json()
    b = requests.get(f"{BASE}/printables?tier=adult", headers=admin_h).json()
    assert [x["id"] for x in a] == [x["id"] for x in b]
    assert requests.get(f"{BASE}/printables?tier=nope", headers=admin_h).status_code == 422


def test_preview_data_has_no_legacy_adult_and_expected_mapping():
    assert pdb.recipes.count_documents({"tier": "adult"}) == 0 and pdb.profiles.count_documents({"tier": "adult"}) == 0
    fam = {r["title"] for r in pdb.recipes.find({"tier": "family"}, {"title": 1})}
    assert {"20-Minute Sheet Pan Salmon", "Weeknight Beef Tacos"} <= fam
    assert pdb.recipes.find_one({"title": "Teen Chef Chicken Stir-Fry"})["tier"] == "teen"


def test_pdf_labels_use_new_names():
    from pypdf import PdfReader
    assert recipe_card.TIER_LABEL["young"] == "Young Chefs (ages 10-12)" and recipe_card.TIER_LABEL["adult"] == "Family Kitchen"
    assert recipe_card.TIER_LABEL["teen"] == "Teen Kitchen (ages 13-15+)"
    for tier, label in (("family", "FAMILY KITCHEN"), ("adult", "FAMILY KITCHEN"), ("young", "YOUNG CHEFS")):
        data, _ = recipe_card.build_recipe_card({"id": "x", "title": "T", "tier": tier, "ingredients": ["a"], "steps": ["b"]})
        assert label in "".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages).upper()
    for banned in ("ADULT KITCHEN", "TEEN CHEFS", "JUNIOR CHEFS"):
        assert banned not in {v.upper() for v in recipe_card.TIER_LABEL.values()}


def test_no_homeschool_first_wording_in_backend_templates():
    src = (Path(server.__file__).parent / "server.py").read_text() + (Path(server.__file__).parent / "email_service.py").read_text()
    assert "for homeschool families" not in src
