"""Iteration 8: FPDF multi_cell fix retest — generated printable PDFs, long titles, journal export, gift-cert long names."""
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
def admin_h():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def demo_h():
    return {"Authorization": f"Bearer {_login(DEMO)}"}


def _assert_valid_pdf(resp, min_size=500):
    assert resp.status_code == 200, resp.text[:300]
    assert "application/pdf" in resp.headers.get("content-type", ""), resp.headers
    # fpdf2 emits %PDF-1.3 header
    assert resp.content[:5] == b"%PDF-", f"bad header: {resp.content[:20]!r}"
    assert len(resp.content) > min_size, f"pdf too small: {len(resp.content)}"


class TestPrintablePDFFix:
    """Retest FPDF multi_cell cursor fix on generated printable path."""

    def test_short_title_generated_pdf(self, admin_h):
        body = {"title": "Iter8 Short", "tier": "junior", "kind": "coloring",
                "description": "Short desc", "content": "Short content body."}
        r = requests.post(f"{API}/printables", json=body, headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        try:
            pdf = requests.get(f"{API}/printables/{pid}/pdf", headers=admin_h, timeout=30)
            _assert_valid_pdf(pdf)
        finally:
            requests.delete(f"{API}/printables/{pid}", headers=admin_h, timeout=15)

    def test_long_title_150chars_generated_pdf(self, admin_h):
        long_title = "The Wonderful Extraordinary Very Long Kitchen Adventure Coloring Page Title That Definitely Exceeds One Hundred Characters For Sure Yes Indeed!"
        assert len(long_title) > 100
        body = {"title": long_title, "tier": "junior", "kind": "coloring",
                "description": "d" * 200, "content": "c" * 500}
        r = requests.post(f"{API}/printables", json=body, headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        try:
            pdf = requests.get(f"{API}/printables/{pid}/pdf", headers=admin_h, timeout=30)
            _assert_valid_pdf(pdf)
        finally:
            requests.delete(f"{API}/printables/{pid}", headers=admin_h, timeout=15)

    def test_uploaded_pdf_still_served(self, admin_h):
        """Regression: printable WITH pdf_file_id should serve the uploaded bytes."""
        body = {"title": "Iter8 Uploaded", "tier": "junior", "kind": "coloring",
                "description": "x", "content": "x"}
        r = requests.post(f"{API}/printables", json=body, headers=admin_h, timeout=15)
        pid = r.json()["id"]
        try:
            marker = b"%PDF-1.4\n%MARKER_ITER8_" + b"z" * 300 + b"\n%%EOF"
            files = {"file": ("m.pdf", io.BytesIO(marker), "application/pdf")}
            up = requests.post(f"{API}/files/upload", headers=admin_h, files=files,
                               data={"purpose": "printable_pdf"}, timeout=15)
            fid = up.json()["file_id"]
            requests.patch(f"{API}/printables/{pid}", json={"pdf_file_id": fid},
                           headers=admin_h, timeout=15)
            pdf = requests.get(f"{API}/printables/{pid}/pdf", headers=admin_h, timeout=30)
            assert pdf.status_code == 200
            assert "application/pdf" in pdf.headers.get("content-type", "")
            assert b"MARKER_ITER8_" in pdf.content
        finally:
            requests.delete(f"{API}/printables/{pid}", headers=admin_h, timeout=15)


class TestJournalExport:
    def test_journal_export_with_flag_enabled(self, admin_h, demo_h):
        # enable the flag
        r = requests.put(f"{API}/admin/flags",
                         json={"flags": {"personalized_pdf_export": True}},
                         headers=admin_h, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("personalized_pdf_export") is True
        try:
            # get demo family's first profile
            profs = requests.get(f"{API}/profiles", headers=demo_h, timeout=15)
            assert profs.status_code == 200, profs.text
            plist = profs.json()
            if not plist:
                pytest.skip("Demo family has no profiles")
            pid = plist[0]["id"]
            pdf = requests.get(f"{API}/journal/{pid}/export", headers=demo_h, timeout=30)
            _assert_valid_pdf(pdf, min_size=300)
        finally:
            # restore flag OFF
            requests.put(f"{API}/admin/flags",
                         json={"flags": {"personalized_pdf_export": False}},
                         headers=admin_h, timeout=15)


class TestGiftCertLongName:
    def test_long_recipient_name(self):
        body = {
            "to": "The Wonderful Extended Baker-Smith Family",
            "from": "Grandma Jean-Marie Wellington-Ashworth",
            "code": "JMK-ITER8-LONGNAME",
            "duration": "annual",
        }
        r = requests.post(f"{API}/gift-certificate/pdf", json=body, timeout=30)
        _assert_valid_pdf(r, min_size=500)
