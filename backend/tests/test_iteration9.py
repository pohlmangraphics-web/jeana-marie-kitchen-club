"""Iteration 9: featured recipe, admin featured toggle, code batch_id + print-sheet PDF, printable download tracking, analytics top_printables."""
import os, pytest, requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@jeanamarie.club", "password": "JeanaAdmin2026!"}
DEMO = {"email": "demo@family.com", "password": "DemoFamily123!"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def demo_h():
    return {"Authorization": f"Bearer {_login(DEMO)}"}


@pytest.fixture(scope="module", autouse=True)
def _cleanup_featured(admin_h):
    yield
    # ensure featured cleared at end
    requests.put(f"{API}/admin/featured-recipe", json={"recipe_id": None}, headers=admin_h, timeout=10)


# ----- Featured recipe -----
class TestFeaturedRecipe:
    def test_clear_then_null_response(self, admin_h, demo_h):
        r = requests.put(f"{API}/admin/featured-recipe", json={"recipe_id": None}, headers=admin_h, timeout=10)
        assert r.status_code == 200, r.text
        g = requests.get(f"{API}/recipes/featured", headers=demo_h, timeout=10)
        assert g.status_code == 200
        assert g.json() == {"recipe": None}

    def test_set_featured_and_read(self, admin_h, demo_h):
        recs = requests.get(f"{API}/recipes", headers=demo_h, timeout=10).json()
        assert recs, "need at least one recipe"
        rid = recs[0]["id"]
        r = requests.put(f"{API}/admin/featured-recipe", json={"recipe_id": rid}, headers=admin_h, timeout=10)
        assert r.status_code == 200, r.text
        g = requests.get(f"{API}/recipes/featured", headers=demo_h, timeout=10)
        assert g.status_code == 200
        body = g.json()
        assert body.get("recipe") is not None
        assert body["recipe"]["id"] == rid
        assert "title" in body["recipe"]

    def test_family_cannot_set_featured(self, demo_h):
        r = requests.put(f"{API}/admin/featured-recipe", json={"recipe_id": None}, headers=demo_h, timeout=10)
        assert r.status_code == 403, r.status_code


# ----- Codes batch_id + print sheet -----
class TestCodesBatchAndPrintSheet:
    def test_bulk_create_shares_batch_id(self, admin_h):
        r = requests.post(f"{API}/admin/codes", json={"count": 3, "duration": "annual"},
                          headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        codes = r.json()
        assert isinstance(codes, list) and len(codes) == 3
        batch_ids = {c.get("batch_id") for c in codes}
        assert len(batch_ids) == 1, f"expected shared batch_id, got {batch_ids}"
        assert None not in batch_ids

    def test_print_sheet_pdf(self, admin_h):
        r = requests.get(f"{API}/admin/codes/print-sheet.pdf", headers=admin_h, timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert "application/pdf" in r.headers.get("content-type", "")
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 400


# ----- Printable download tracking -----
class TestPrintableDownloadTracking:
    def test_download_count_increments(self, admin_h):
        body = {"title": "Iter9 Tracking", "tier": "junior", "kind": "coloring",
                "description": "d", "content": "c"}
        r = requests.post(f"{API}/printables", json=body, headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        try:
            for _ in range(2):
                pdf = requests.get(f"{API}/printables/{pid}/pdf", headers=admin_h, timeout=30)
                assert pdf.status_code == 200
            a = requests.get(f"{API}/admin/analytics", headers=admin_h, timeout=15)
            assert a.status_code == 200, a.text
            top = a.json().get("top_printables")
            assert isinstance(top, list)
            match = next((x for x in top if x["title"] == "Iter9 Tracking"), None)
            assert match is not None, f"printable not in top_printables: {top}"
            assert isinstance(match["download_count"], int)
            assert match["download_count"] >= 2
            assert "tier" in match and "kind" in match
        finally:
            requests.delete(f"{API}/printables/{pid}", headers=admin_h, timeout=15)


# ----- Regression -----
class TestRegression:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200

    def test_samples(self):
        r = requests.get(f"{API}/recipes/samples", timeout=10)
        assert r.status_code == 200

    def test_recipes_list(self, demo_h):
        r = requests.get(f"{API}/recipes", headers=demo_h, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_printables_list(self, demo_h):
        r = requests.get(f"{API}/printables", headers=demo_h, timeout=10)
        assert r.status_code == 200

    def test_gift_cert_pdf(self):
        body = {"to": "Alice", "from": "Bob", "code": "JMK-ITER9-REG", "duration": "annual"}
        r = requests.post(f"{API}/gift-certificate/pdf", json=body, timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
