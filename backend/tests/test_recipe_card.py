"""Recipe-card PDFs: generator (unit) + endpoint (uploaded preference, stub fallback, auth, no mutation).
Creates & removes its own test recipe/files; never touches real recipes."""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(__file__)); from creds import ADMIN_PASSWORD as _ADMIN_PW, DEMO_PASSWORD as _DEMO_PW  # noqa: E402
import io
import os
import sys
import copy
import uuid
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient
from fpdf import FPDF
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # noqa: E702
from recipe_card import build_recipe_card  # noqa: E402

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
pdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ADMIN = {"email": "admin@jeanamarie.club", "password": _ADMIN_PW}
STUB = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"  # the broken Kabobs (Copy) card bytes

SHORT = {"id": "s", "title": "Toast", "tier": "little", "ingredients": ["bread"], "steps": ["Toast it."]}
LONG = {"id": "l", "title": "Grandma's Sunday Pot Roast with Root Vegetables & Herb Gravy — Long Title", "tier": "teen",
        "description": "A long description. " * 12, "prep_time": 45, "cook_time": 180, "servings": 8,
        "ingredients": [f"{n}½ cups ingredient número {n} — ¼ tsp «special» ✓ ⅓" for n in range(1, 31)],
        "steps": [f"Step {n}: " + "Stir constantly so nothing sticks. " * 6 for n in range(1, 26)],
        "homeschool_topic": "Fractions ½ ¼ ⅓", "lesson_plan": "Long lesson plan. " * 40,
        "safety_notes": ["Hot oven — adult help required"], "tips": "Rest 15 minutes.", "published_at": "2026-01-01T00:00:00+00:00"}


def _pages(data): return PdfReader(io.BytesIO(data), strict=False).pages
def _text(data): return "".join(p.extract_text() or "" for p in _pages(data))


# ---------------- generator unit tests ----------------
def test_short_recipe_missing_optional_fields_and_no_image():
    data, meta = build_recipe_card(SHORT)
    assert data.startswith(b"%PDF") and len(_pages(data)) == 1 and meta == {"pages": 1, "size": len(data), "image_included": False}
    t = _text(data)
    assert "Toast" in t and "bread" in t and "Toast it." in t and "INGREDIENTS" in t and "INSTRUCTIONS" in t
    assert "LEARNING" not in t and "SAFETY" not in t and "TIPS" not in t  # absent sections are not invented


def test_long_recipe_multipage_no_blank_pages_special_chars():
    data, meta = build_recipe_card(LONG)
    pages = _pages(data)
    assert meta["pages"] == len(pages) >= 3
    assert all((p.extract_text() or "").strip() for p in pages), "blank page"
    t = _text(data)
    for s in ("½", "¼", "⅓", "«special»", "✓", "—", "número", "SAFETY & ADULT HELP", "TIPS", "LEARNING ACTIVITY", "Page 1 of"):
        assert s in t, s
    assert "Step 25:" in t and "30½ cups" in t  # nothing truncated


def test_content_rendered_verbatim_and_input_not_mutated():
    src = copy.deepcopy(LONG)
    data, _ = build_recipe_card(src)
    assert src == LONG  # generator never mutates its input
    t = _text(data).replace("\n", " ")
    for ing in LONG["ingredients"][:5]: assert ing in t
    assert LONG["tips"] in t and LONG["safety_notes"][0] in t


def test_pdf_metadata_letter_size_and_determinism():
    d1, _ = build_recipe_card(SHORT); d2, _ = build_recipe_card(SHORT)
    assert d1 == d2, "generator must be deterministic"
    rd = PdfReader(io.BytesIO(d1))
    assert rd.metadata["/Title"] == "Toast - Recipe Card" and rd.metadata["/Author"] == "Jeana Marie's Kitchen Club"
    w, h = float(rd.pages[0].mediabox.width), float(rd.pages[0].mediabox.height)
    assert abs(w - 612) < 1 and abs(h - 792) < 1  # US Letter in points


def test_image_included_when_valid_and_skipped_when_broken():
    from PIL import Image
    buf = io.BytesIO(); Image.new("RGB", (900, 300), (200, 50, 50)).save(buf, "PNG")
    r = {**SHORT, "photo_file_id": "pf"}
    data, meta = build_recipe_card(r, get_object=lambda fid: (buf.getvalue(), "image/png"))
    assert meta["image_included"] and len(_pages(data)) == 1
    data, meta = build_recipe_card(r, get_object=lambda fid: (b"not an image", "image/png"))
    assert not meta["image_included"] and len(_pages(data)) == 1
    data, meta = build_recipe_card({**SHORT, "photo_url": "http://insecure.example/x.jpg"})
    assert not meta["image_included"]


# ---------------- endpoint tests ----------------
@pytest.fixture(scope="module")
def admin_h():
    r = requests.post(f"{BASE}/auth/login", json=ADMIN); assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def nonmember_h():
    u = pdb.users.find_one({"role": "family", "membership_expires_at": None, "email": {"$regex": "^test_"}})
    assert u, "need an existing non-member test account"
    import server
    return {"Authorization": f"Bearer {server.make_token(u['id'], u['role'])}"}


@pytest.fixture(scope="module")
def member_h():
    u = pdb.users.find_one({"email": "pohlmangraphics@gmail.com"})
    import server
    return {"Authorization": f"Bearer {server.make_token(u['id'], u['role'])}"}


def _real_pdf(marker="UPLOADED-CARD-MARKER"):
    p = FPDF(); p.add_page(); p.set_font("helvetica", size=14); p.cell(text=marker); return bytes(p.output())


def _upload(h, data, name="TEST_card.pdf", ctype="application/pdf"):
    return requests.post(f"{BASE}/files/upload", headers=h, data={"purpose": "recipe_card"}, files={"file": (name, data, ctype)})


@pytest.fixture(scope="module")
def recipe(admin_h):
    body = {"title": f"TEST Card Recipe {uuid.uuid4().hex[:6]}", "tier": "adult", "description": "Test desc", "ingredients": ["1 cup TEST"],
            "steps": ["Do TEST step"], "prep_time": 1, "cook_time": 2, "servings": 3, "is_sample": False, "homeschool_topic": "TEST topic"}
    r = requests.post(f"{BASE}/recipes", headers=admin_h, json=body); assert r.status_code == 200, r.text
    rec = r.json()
    yield rec
    pdb.recipes.delete_one({"id": rec["id"]})
    pdb.files.delete_many({"original_filename": {"$regex": "^TEST_"}})


def _attach(admin_h, rid, file_id):
    assert requests.patch(f"{BASE}/recipes/{rid}", headers=admin_h, json={"recipe_card_file_id": file_id}).status_code == 200


def _card(h, rid, **params): return requests.get(f"{BASE}/recipes/{rid}/card", headers=h, params=params)


def test_generated_card_when_nothing_uploaded(admin_h, recipe):
    r = _card(admin_h, recipe["id"])
    assert r.status_code == 200 and r.headers["x-recipe-card-source"] == "generated"
    assert r.headers["content-type"].startswith("application/pdf") and r.content.startswith(b"%PDF")
    assert r.headers["content-disposition"] == f'attachment; filename="{recipe["title"].replace(" ", "_")}_Recipe_Card.pdf"'
    assert "1 cup TEST" in _text(r.content) and "Do TEST step" in _text(r.content)


def test_uploaded_valid_pdf_is_preferred(admin_h, recipe):
    up = _upload(admin_h, _real_pdf()); assert up.status_code == 200, up.text
    _attach(admin_h, recipe["id"], up.json()["file_id"])
    r = _card(admin_h, recipe["id"])
    assert r.status_code == 200 and r.headers["x-recipe-card-source"] == "uploaded" and "UPLOADED-CARD-MARKER" in _text(r.content)
    g = _card(admin_h, recipe["id"], source="generated")
    assert g.headers["x-recipe-card-source"] == "generated" and "UPLOADED-CARD-MARKER" not in _text(g.content)


def test_invalid_stub_falls_back_to_generated(admin_h, recipe):
    from storage import put_object, APP_NAME
    fid = str(uuid.uuid4())
    res = put_object(f"{APP_NAME}/recipe_card/test/{fid}.pdf", STUB, "application/pdf")
    pdb.files.insert_one({"id": fid, "storage_path": res["path"], "purpose": "recipe_card", "original_filename": "TEST_legacy_stub.pdf",
                          "content_type": "application/pdf", "size": len(STUB), "uploaded_by": "test", "is_deleted": False, "created_at": "2026-01-01T00:00:00+00:00"})
    _attach(admin_h, recipe["id"], fid)
    r = _card(admin_h, recipe["id"])
    assert r.status_code == 200 and r.headers["x-recipe-card-source"] == "generated" and len(_pages(r.content)) >= 1


def test_missing_object_falls_back_to_generated(admin_h, recipe):
    fid = str(uuid.uuid4())
    pdb.files.insert_one({"id": fid, "storage_path": f"does/not/exist/{fid}.pdf", "purpose": "recipe_card", "original_filename": "TEST_missing.pdf",
                          "content_type": "application/pdf", "size": 0, "uploaded_by": "test", "is_deleted": False, "created_at": "2026-01-01T00:00:00+00:00"})
    _attach(admin_h, recipe["id"], fid)
    r = _card(admin_h, recipe["id"]); assert r.status_code == 200 and r.headers["x-recipe-card-source"] == "generated"
    pdb.recipes.update_one({"id": recipe["id"]}, {"$set": {"recipe_card_file_id": "no-such-file"}})
    r = _card(admin_h, recipe["id"]); assert r.status_code == 200 and r.headers["x-recipe-card-source"] == "generated"


def test_upload_rejects_stub_and_non_pdf(admin_h):
    assert _upload(admin_h, STUB, "TEST_stub.pdf").status_code == 422
    assert _upload(admin_h, b"hello world", "TEST_text.pdf").status_code == 422


def test_authorization_matrix(admin_h, nonmember_h, member_h, recipe):
    assert _card({}, recipe["id"]).status_code == 401
    assert _card(nonmember_h, recipe["id"]).status_code == 402
    assert _card(member_h, recipe["id"]).status_code == 200
    assert _card(admin_h, recipe["id"]).status_code == 200
    assert requests.post(f"{BASE}/admin/recipes/{recipe['id']}/card/generate").status_code == 401
    assert requests.post(f"{BASE}/admin/recipes/{recipe['id']}/card/generate", headers=member_h).status_code == 403
    assert requests.get(f"{BASE}/recipes/{uuid.uuid4()}/card", headers=admin_h).status_code == 404


def test_admin_generate_reports_metadata_and_does_not_mutate(admin_h, recipe):
    before = pdb.recipes.find_one({"id": recipe["id"]}, {"_id": 0})
    r = requests.post(f"{BASE}/admin/recipes/{recipe['id']}/card/generate", headers=admin_h)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] and body["pages"] >= 1 and body["size"] > 1000 and body["filename"].endswith("_Recipe_Card.pdf")
    assert set(body) == {"ok", "pages", "size", "image_included", "uploaded_card_valid", "served_source", "filename"}
    assert pdb.recipes.find_one({"id": recipe["id"]}, {"_id": 0}) == before


def test_live_kabobs_copy_now_serves_generated_card_and_record_untouched(admin_h):
    rid = "a3f29d4d-16ce-4273-8da7-0c26db31e91a"
    before = pdb.recipes.find_one({"id": rid}, {"_id": 0})
    r = _card(admin_h, rid)
    assert r.status_code == 200 and r.headers["x-recipe-card-source"] == "generated" and len(_pages(r.content)) == 1
    t = _text(r.content).replace("\n", " ")
    assert "Rainbow Fruit Kabobs (Copy)" in t and "strawberries" in t
    assert pdb.recipes.find_one({"id": rid}, {"_id": 0}) == before and before["recipe_card_file_id"] == "de421242-e475-4a86-a063-e037b2d7ba6d"
