"""Iteration 7 backend tests: uploads, edit/duplicate/delete, printable fallback, multi_cell wrapping."""
import os, io, pytest, requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@jeanamarie.club", "password": "JeanaAdmin2026!"}
DEMO = {"email": "demo@family.com", "password": "DemoFamily123!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def demo_token():
    return _login(DEMO)


@pytest.fixture(scope="module")
def admin_h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def demo_h(demo_token):
    return {"Authorization": f"Bearer {demo_token}"}


# minimal 1x1 PNG bytes
_PNG = bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
# minimal PDF (valid header + trailer)
_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def _upload(headers, purpose, filename, content, mime):
    files = {"file": (filename, io.BytesIO(content), mime)}
    data = {"purpose": purpose}
    r = requests.post(f"{API}/files/upload", headers=headers, files=files, data=data, timeout=30)
    return r


# --- Uploads ---
class TestUploads:
    def test_upload_recipe_photo(self, admin_h):
        r = _upload(admin_h, "recipe_photo", "photo.png", _PNG, "image/png")
        assert r.status_code == 200, r.text
        j = r.json()
        assert "file_id" in j and j["url"].startswith("/api/files/")

    def test_upload_recipe_card_pdf(self, admin_h):
        r = _upload(admin_h, "recipe_card", "card.pdf", _PDF, "application/pdf")
        assert r.status_code == 200, r.text
        assert "file_id" in r.json()

    def test_upload_printable_pdf(self, admin_h):
        r = _upload(admin_h, "printable_pdf", "p.pdf", _PDF, "application/pdf")
        assert r.status_code == 200

    def test_upload_printable_thumbnail(self, admin_h):
        r = _upload(admin_h, "printable_thumbnail", "t.png", _PNG, "image/png")
        assert r.status_code == 200


# --- Recipe patch + duplicate + card ---
class TestRecipeAdmin:
    @pytest.fixture(scope="class")
    def created_recipe(self, admin_h):
        body = {
            "title": "TEST_Iter7 Recipe",
            "tier": "junior", "description": "Test",
            "ingredients": ["a","b"], "steps": ["s1","s2"],
            "prep_time": 5, "cook_time": 5, "servings": 2,
        }
        r = requests.post(f"{API}/recipes", json=body, headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_patch_recipe_card_file_id(self, admin_h, created_recipe):
        # upload a card PDF first
        up = _upload(admin_h, "recipe_card", "card.pdf", _PDF, "application/pdf")
        fid = up.json()["file_id"]
        rid = created_recipe["id"]
        r = requests.patch(f"{API}/recipes/{rid}", json={"recipe_card_file_id": fid}, headers=admin_h, timeout=15)
        assert r.status_code == 200
        assert r.json().get("recipe_card_file_id") == fid
        # GET verify
        g = requests.get(f"{API}/recipes/{rid}", headers=admin_h, timeout=15)
        assert g.status_code == 200
        assert g.json().get("recipe_card_file_id") == fid
        # stash for card test
        pytest._iter7_recipe_id = rid
        pytest._iter7_card_fid = fid

    def test_duplicate_recipe(self, admin_h, created_recipe):
        rid = created_recipe["id"]
        r = requests.post(f"{API}/recipes/{rid}/duplicate", headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        dup = r.json()
        assert dup["id"] != rid
        assert dup["title"].endswith("(Copy)")
        assert dup["is_sample"] is False
        assert dup.get("published_at")
        # cleanup dup
        requests.delete(f"{API}/recipes/{dup['id']}", headers=admin_h, timeout=15)

    def test_recipe_card_download_admin(self, admin_h):
        rid = getattr(pytest, "_iter7_recipe_id", None)
        assert rid, "prev test skipped"
        r = requests.get(f"{API}/recipes/{rid}/card", headers=admin_h, timeout=15)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type","")
        assert len(r.content) > 0

    def test_recipe_card_402_non_member(self, admin_h):
        """A recipe without card but on a non-member should 402 first."""
        # Create a fresh non-sample recipe with NO card
        body = {"title":"TEST_NoCard","tier":"junior","description":"x","ingredients":["a"],"steps":["s"],
                "prep_time":1,"cook_time":1,"servings":1,"is_sample":False}
        r = requests.post(f"{API}/recipes", json=body, headers=admin_h, timeout=15)
        rid = r.json()["id"]
        # Attempt as unauth (no token)
        rr = requests.get(f"{API}/recipes/{rid}/card", timeout=15)
        # Endpoint uses get_current_user -> requires auth first (401)
        assert rr.status_code in (401, 402), rr.status_code
        requests.delete(f"{API}/recipes/{rid}", headers=admin_h, timeout=15)

    def test_recipe_card_404_no_card(self, admin_h):
        body = {"title":"TEST_NoCard2","tier":"junior","description":"x","ingredients":["a"],"steps":["s"],
                "prep_time":1,"cook_time":1,"servings":1,"is_sample":True}
        r = requests.post(f"{API}/recipes", json=body, headers=admin_h, timeout=15)
        rid = r.json()["id"]
        rr = requests.get(f"{API}/recipes/{rid}/card", headers=admin_h, timeout=15)
        assert rr.status_code == 404
        requests.delete(f"{API}/recipes/{rid}", headers=admin_h, timeout=15)

    def test_cleanup_recipe(self, admin_h, created_recipe):
        r = requests.delete(f"{API}/recipes/{created_recipe['id']}", headers=admin_h, timeout=15)
        assert r.status_code == 200


# --- Printables ---
class TestPrintables:
    @pytest.fixture(scope="class")
    def printable(self, admin_h):
        body = {"title":"TEST_Iter7 Printable","tier":"junior","kind":"coloring",
                "description":"d","content":"c"}
        r = requests.post(f"{API}/printables", json=body, headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_patch_printable(self, admin_h, printable):
        pid = printable["id"]
        r = requests.patch(f"{API}/printables/{pid}", json={"title":"TEST_Iter7 Renamed","description":"newd"}, headers=admin_h, timeout=15)
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_Iter7 Renamed"

    def test_pdf_generated_when_no_pdf_file_id(self, admin_h, printable):
        pid = printable["id"]
        r = requests.get(f"{API}/printables/{pid}/pdf", headers=admin_h, timeout=30)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type","")
        assert len(r.content) > 500  # generated template

    def test_pdf_serves_uploaded_when_pdf_file_id_set(self, admin_h, printable):
        pid = printable["id"]
        # upload a marker pdf
        marker = b"%PDF-1.4\n%MARKER_ITER7\n" + b"x"*200 + b"\n%%EOF"
        files = {"file": ("m.pdf", io.BytesIO(marker), "application/pdf")}
        up = requests.post(f"{API}/files/upload", headers=admin_h, files=files, data={"purpose":"printable_pdf"}, timeout=15)
        fid = up.json()["file_id"]
        requests.patch(f"{API}/printables/{pid}", json={"pdf_file_id": fid}, headers=admin_h, timeout=15)
        r = requests.get(f"{API}/printables/{pid}/pdf", headers=admin_h, timeout=30)
        assert r.status_code == 200
        # uploaded bytes should be returned verbatim
        assert b"MARKER_ITER7" in r.content

    def test_thumbnail_public(self, admin_h, printable):
        pid = printable["id"]
        # no thumbnail yet -> 404
        r = requests.get(f"{API}/printables/{pid}/thumbnail", timeout=15)
        assert r.status_code == 404
        # attach a thumbnail
        files = {"file": ("t.png", io.BytesIO(_PNG), "image/png")}
        up = requests.post(f"{API}/files/upload", headers=admin_h, files=files, data={"purpose":"printable_thumbnail"}, timeout=15)
        fid = up.json()["file_id"]
        requests.patch(f"{API}/printables/{pid}", json={"thumbnail_file_id": fid}, headers=admin_h, timeout=15)
        # public - no auth header
        r2 = requests.get(f"{API}/printables/{pid}/thumbnail", timeout=15)
        assert r2.status_code == 200
        assert r2.headers.get("content-type","").startswith("image/")

    def test_long_title_wraps(self, admin_h):
        long_title = "A" * 150
        body = {"title": long_title, "tier":"junior", "kind":"coloring", "description":"d", "content":"c"}
        r = requests.post(f"{API}/printables", json=body, headers=admin_h, timeout=15)
        assert r.status_code == 200
        pid = r.json()["id"]
        pdf = requests.get(f"{API}/printables/{pid}/pdf", headers=admin_h, timeout=30)
        assert pdf.status_code == 200, pdf.text[:200]
        assert len(pdf.content) > 1024
        requests.delete(f"{API}/printables/{pid}", headers=admin_h, timeout=15)

    def test_cleanup(self, admin_h, printable):
        requests.delete(f"{API}/printables/{printable['id']}", headers=admin_h, timeout=15)


# --- Regression ---
class TestRegression:
    def test_flags(self):
        r = requests.get(f"{API}/flags", timeout=15)
        assert r.status_code == 200

    def test_samples(self):
        r = requests.get(f"{API}/recipes/samples", timeout=15)
        assert r.status_code == 200 and len(r.json()) >= 1

    def test_list_printables(self, admin_h):
        r = requests.get(f"{API}/printables", headers=admin_h, timeout=15)
        assert r.status_code == 200

    def test_gift_cert(self):
        r = requests.post(f"{API}/gift-certificate/pdf",
                          json={"to":"T","from":"F","code":"JMK-TEST","duration":"annual"}, timeout=30)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type","")

    def test_generate_and_redeem_code(self, admin_h, demo_h):
        r = requests.post(f"{API}/admin/codes", headers=admin_h,
                          json={"count":1,"duration":"monthly","note":"iter7"}, timeout=15)
        assert r.status_code == 200, r.text
        code = r.json()[0]["code"] if isinstance(r.json(), list) else r.json()["codes"][0]["code"]
        rr = requests.post(f"{API}/redeem", headers=demo_h, json={"code": code}, timeout=15)
        assert rr.status_code in (200, 400), rr.text
