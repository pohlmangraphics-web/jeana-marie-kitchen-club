"""Iteration 17: Verify family-member download of 'Food Group Match' printable."""
import os
import hashlib
import io
import pytest
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(__file__)); from creds import DEMO
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://recipe-journal-club.preview.emergentagent.com").rstrip("/")
PID = "924178ba-9f25-45c3-a6a8-f82530f0c1b3"
SIBLING_PID = "6894d221-3a53-423e-870e-a29ce6745a54"
SOURCE_PDF_URL = "https://customer-assets-m6fa6gv7.emergentagent.net/job_recipe-journal-club/artifacts/pxijsmd6_Kitchen%20Club%20Food%20Group.pdf"


@pytest.fixture(scope="module")
def family_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json=DEMO,
                      timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(family_token):
    return {"Authorization": f"Bearer {family_token}"}


@pytest.fixture(scope="module")
def source_sha():
    r = requests.get(SOURCE_PDF_URL, timeout=60)
    assert r.status_code == 200
    return hashlib.sha256(r.content).hexdigest(), len(r.content)


# Printables list
def test_printables_list(auth_headers):
    r = requests.get(f"{BASE_URL}/api/printables", headers=auth_headers, timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 8, f"expected 8 printables, got {len(items)}: titles={[i['title'] for i in items]}"
    matches = [i for i in items if i["id"] == PID]
    assert len(matches) == 1
    p = matches[0]
    assert p["title"] == "Food Group Match"
    assert p["tier"] == "junior"
    assert p["kind"] == "food_id"
    assert p["description"] == "Draw a line from each food group name to the matching picture."
    # No other with same title
    same_title = [i for i in items if i["title"] == "Food Group Match"]
    assert len(same_title) == 1


def test_printables_tier_junior_includes_food_group(auth_headers):
    r = requests.get(f"{BASE_URL}/api/printables?tier=junior", headers=auth_headers, timeout=30)
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()]
    assert PID in ids


# PDF download
def test_pdf_download_food_group_match(auth_headers, source_sha):
    src_sha, src_len = source_sha
    r = requests.get(f"{BASE_URL}/api/printables/{PID}/pdf", headers=auth_headers, timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert 'filename="Food_Group_Match.pdf"' in cd, f"CD={cd}"
    assert r.content[:4] == b"%PDF"
    assert len(r.content) == 102663, f"got {len(r.content)}"
    assert hashlib.sha256(r.content).hexdigest() == src_sha
    # pypdf page count
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) == 1


def test_pdf_download_unauthenticated():
    r = requests.get(f"{BASE_URL}/api/printables/{PID}/pdf", timeout=30)
    assert r.status_code == 401


def test_sibling_regression(auth_headers):
    r = requests.get(f"{BASE_URL}/api/printables/{SIBLING_PID}/pdf", headers=auth_headers, timeout=60)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(r.content))
    assert len(reader.pages) == 1


def test_readonly_final_state(auth_headers):
    r = requests.get(f"{BASE_URL}/api/printables", headers=auth_headers, timeout=30)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 8
    p = next(i for i in items if i["id"] == PID)
    assert p.get("pdf_file_id") == "7be730c8-6391-4bc2-a27c-a8b2249b8ad2"
