"""Iteration 15 supplementary tests for recipe card generation."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(__file__)); from creds import ADMIN_PASSWORD as _ADMIN_PW, DEMO_PASSWORD as _DEMO_PW  # noqa: E402
import io
import os
import time
import pytest
import requests
from pypdf import PdfReader
from fpdf import FPDF

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()

ADMIN = ("admin@jeanamarie.club", _ADMIN_PW)
DEMO = ("demo@family.com", _DEMO_PW)

KABOBS_COPY = "a3f29d4d-16ce-4273-8da7-0c26db31e91a"
KABOBS_ORIG = "502ef474-b8a0-4f5e-8188-d09af0fd0bce"
EXPECTED_CARD_FILE_ID = "de421242-e475-4a86-a063-e037b2d7ba6d"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def demo_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": DEMO[0], "password": DEMO[1]})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_kabobs_copy_card_generated(admin_token):
    """GET card for kabobs copy → generated (its uploaded 45-byte stub is invalid)."""
    r = requests.get(f"{BASE_URL}/api/recipes/{KABOBS_COPY}/card", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.headers.get("X-Recipe-Card-Source") == "generated"
    cd = r.headers.get("Content-Disposition", "")
    assert 'filename="Rainbow_Fruit_Kabobs_Copy_Recipe_Card.pdf"' in cd, cd
    assert r.content[:4] == b"%PDF"
    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text() or ""
    assert "Rainbow Fruit Kabobs" in text
    assert "strawberries" in text.lower()


def test_kabobs_copy_recipe_file_id_unchanged(admin_token):
    r = requests.get(f"{BASE_URL}/api/recipes/{KABOBS_COPY}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json().get("recipe_card_file_id") == EXPECTED_CARD_FILE_ID


def test_kabobs_orig_card_generated(admin_token):
    r = requests.get(f"{BASE_URL}/api/recipes/{KABOBS_ORIG}/card", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.headers.get("X-Recipe-Card-Source") == "generated"
    assert r.content[:4] == b"%PDF"
    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) == 1


def test_get_card_no_token():
    r = requests.get(f"{BASE_URL}/api/recipes/{KABOBS_COPY}/card")
    assert r.status_code == 401


def test_post_generate_no_token():
    r = requests.post(f"{BASE_URL}/api/admin/recipes/{KABOBS_COPY}/card/generate")
    assert r.status_code == 401


def test_post_generate_demo_forbidden(demo_token):
    r = requests.post(f"{BASE_URL}/api/admin/recipes/{KABOBS_COPY}/card/generate", headers=_auth(demo_token))
    assert r.status_code == 403


def test_post_generate_admin_keys(admin_token):
    r = requests.post(f"{BASE_URL}/api/admin/recipes/{KABOBS_COPY}/card/generate", headers=_auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    expected = {"ok", "pages", "size", "image_included", "uploaded_card_valid", "served_source", "filename"}
    assert set(data.keys()) == expected, f"got={set(data.keys())}"
    assert data["uploaded_card_valid"] is False


def test_uploaded_valid_pdf_preference(admin_token):
    """Create throwaway recipe, upload valid PDF, verify preference then cleanup."""
    marker = f"MARKERTOKENQA{int(time.time())}"
    # Create recipe
    payload = {
        "title": f"TEST QA Card {int(time.time())}",
        "description": "throwaway",
        "ingredients": ["1 cup flour"],
        "steps": ["mix"],
        "servings": 1,
        "prep_time_min": 1,
        "cook_time_min": 1,
        "difficulty": "easy",
        "tags": ["test"],
        "age_range": "all",
        "published": True,
        "tier": "little",
    }
    r = requests.post(f"{BASE_URL}/api/recipes", json=payload, headers=_auth(admin_token))
    assert r.status_code in (200, 201), r.text
    rid = r.json()["id"]

    try:
        # Build a valid one-page PDF with unique marker
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=14)
        pdf.cell(0, 10, marker)
        pdf_bytes = bytes(pdf.output())
        assert pdf_bytes[:4] == b"%PDF"

        # Upload as recipe_card
        files = {"file": ("card.pdf", pdf_bytes, "application/pdf")}
        data = {"purpose": "recipe_card"}
        r = requests.post(f"{BASE_URL}/api/files/upload", files=files, data=data, headers=_auth(admin_token))
        assert r.status_code in (200, 201), r.text
        file_id = r.json()["file_id"]

        # Patch recipe
        r = requests.patch(f"{BASE_URL}/api/recipes/{rid}", json={"recipe_card_file_id": file_id}, headers=_auth(admin_token))
        assert r.status_code == 200, r.text

        # GET card default → uploaded
        r = requests.get(f"{BASE_URL}/api/recipes/{rid}/card", headers=_auth(admin_token))
        assert r.status_code == 200
        assert r.headers.get("X-Recipe-Card-Source") == "uploaded", r.headers
        reader = PdfReader(io.BytesIO(r.content))
        found_marker = any(marker in (p.extract_text() or "") for p in reader.pages)
        assert found_marker, "marker not found in uploaded PDF"

        # GET card?source=generated → generated
        r = requests.get(f"{BASE_URL}/api/recipes/{rid}/card?source=generated", headers=_auth(admin_token))
        assert r.status_code == 200
        assert r.headers.get("X-Recipe-Card-Source") == "generated"
    finally:
        # Cleanup: delete recipe (best effort)
        requests.delete(f"{BASE_URL}/api/recipes/{rid}", headers=_auth(admin_token))
