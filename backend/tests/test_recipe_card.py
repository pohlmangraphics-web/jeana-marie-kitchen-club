"""Recipe-card PDF download: valid PDF, stub/corrupt PDF, missing object, auth. Creates & removes its own test recipe."""
import io
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from fpdf import FPDF

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
pdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ADMIN = {"email": "admin@jeanamarie.club", "password": "JeanaAdmin2026!"}
STUB = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"  # what the broken Kabobs (Copy) card contains


def _real_pdf() -> bytes:
    p = FPDF(); p.add_page(); p.set_font("helvetica", size=14); p.cell(text="TEST recipe card"); return bytes(p.output())


@pytest.fixture(scope="module")
def admin_h():
    r = requests.post(f"{BASE}/auth/login", json=ADMIN); assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def nonmember_h():
    u = pdb.users.find_one({"role": "family", "membership_expires_at": None, "email": {"$regex": "^test_"}})
    assert u, "need an existing non-member test account"
    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import server
    return {"Authorization": f"Bearer {server.make_token(u['id'], u['role'])}"}


def _upload(h, data, name="card.pdf", ctype="application/pdf"):
    return requests.post(f"{BASE}/files/upload", headers=h, data={"purpose": "recipe_card"}, files={"file": (name, data, ctype)})


@pytest.fixture(scope="module")
def recipe(admin_h):
    body = {"title": f"TEST Card Recipe {uuid.uuid4().hex[:6]}", "tier": "adult", "description": "t", "ingredients": ["a"], "steps": ["b"],
            "prep_time": 1, "cook_time": 1, "servings": 1, "is_sample": False}
    r = requests.post(f"{BASE}/recipes", headers=admin_h, json=body); assert r.status_code == 200, r.text
    rec = r.json()
    yield rec
    pdb.recipes.delete_one({"id": rec["id"]})
    pdb.files.delete_many({"original_filename": {"$regex": "^TEST_"}})


def _attach(admin_h, rid, file_id):
    r = requests.patch(f"{BASE}/recipes/{rid}", headers=admin_h, json={"recipe_card_file_id": file_id}); assert r.status_code == 200


def test_upload_rejects_stub_and_non_pdf(admin_h):
    assert _upload(admin_h, STUB, "TEST_stub.pdf").status_code == 422
    assert _upload(admin_h, b"hello world", "TEST_text.pdf").status_code == 422
    assert _upload(admin_h, b"", "TEST_empty.pdf").status_code == 422


def test_valid_pdf_download(admin_h, recipe):
    up = _upload(admin_h, _real_pdf(), "TEST_real.pdf"); assert up.status_code == 200, up.text
    _attach(admin_h, recipe["id"], up.json()["file_id"])
    r = requests.get(f"{BASE}/recipes/{recipe['id']}/card", headers=admin_h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF") and len(r.content) > 500
    assert "attachment" in r.headers["content-disposition"]
    from pypdf import PdfReader
    assert len(PdfReader(io.BytesIO(r.content)).pages) == 1


def test_stub_pdf_returns_422_not_broken_viewer(admin_h, recipe):
    # Simulate legacy stub uploaded before validation existed (bypass upload check by writing the DB/file record directly)
    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    from storage import put_object, APP_NAME
    fid = str(uuid.uuid4())
    res = put_object(f"{APP_NAME}/recipe_card/test/{fid}.pdf", STUB, "application/pdf")
    pdb.files.insert_one({"id": fid, "storage_path": res["path"], "purpose": "recipe_card", "original_filename": "TEST_legacy_stub.pdf",
                          "content_type": "application/pdf", "size": len(STUB), "uploaded_by": "test", "is_deleted": False, "created_at": "2026-01-01T00:00:00+00:00"})
    _attach(admin_h, recipe["id"], fid)
    r = requests.get(f"{BASE}/recipes/{recipe['id']}/card", headers=admin_h)
    assert r.status_code == 422 and "valid PDF" in r.json()["detail"]


def test_missing_object_returns_404(admin_h, recipe):
    fid = str(uuid.uuid4())
    pdb.files.insert_one({"id": fid, "storage_path": f"does/not/exist/{fid}.pdf", "purpose": "recipe_card", "original_filename": "TEST_missing.pdf",
                          "content_type": "application/pdf", "size": 0, "uploaded_by": "test", "is_deleted": False, "created_at": "2026-01-01T00:00:00+00:00"})
    _attach(admin_h, recipe["id"], fid)
    r = requests.get(f"{BASE}/recipes/{recipe['id']}/card", headers=admin_h)
    assert r.status_code == 404 and isinstance(r.json()["detail"], str)
    pdb.recipes.update_one({"id": recipe["id"]}, {"$set": {"recipe_card_file_id": "no-such-file"}})
    assert requests.get(f"{BASE}/recipes/{recipe['id']}/card", headers=admin_h).status_code == 404


def test_authorization(admin_h, nonmember_h, recipe):
    up = _upload(admin_h, _real_pdf(), "TEST_real2.pdf"); _attach(admin_h, recipe["id"], up.json()["file_id"])
    assert requests.get(f"{BASE}/recipes/{recipe['id']}/card").status_code == 401
    assert requests.get(f"{BASE}/recipes/{recipe['id']}/card", headers=nonmember_h).status_code == 402
    assert requests.get(f"{BASE}/recipes/{recipe['id']}/card", headers=admin_h).status_code == 200


def test_live_kabobs_copy_card_is_diagnosed_as_invalid(admin_h):
    """Documents the reported bug: the attached card is a 45-byte zero-page stub → now 422 instead of a broken viewer."""
    r = requests.get(f"{BASE}/recipes/a3f29d4d-16ce-4273-8da7-0c26db31e91a/card", headers=admin_h)
    assert r.status_code == 422
