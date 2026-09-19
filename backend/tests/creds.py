"""Test credentials come from the environment (or the untracked memory/test_credentials.md). Never hardcode passwords."""
import os
import re
from pathlib import Path

_MEMO = Path(__file__).resolve().parents[2] / "memory" / "test_credentials.md"


def _from_memo(section: str, field: str) -> str:
    if not _MEMO.exists(): return ""
    txt = _MEMO.read_text()
    block = re.split(r"^## ", txt, flags=re.M)
    for b in block:
        if b.lower().startswith(section.lower()):
            m = re.search(rf"{field}:\s*`([^`]+)`", b)
            if m: return m.group(1)
    return ""


def _cred(env_name: str, section: str, field: str) -> str:
    val = os.environ.get(env_name, "").strip() or _from_memo(section, field)
    if not val:
        raise RuntimeError(f"{env_name} not set and not found in memory/test_credentials.md")
    return val


ADMIN_EMAIL = _cred("TEST_ADMIN_EMAIL", "Admin", "Email")
ADMIN_PASSWORD = _cred("TEST_ADMIN_PASSWORD", "Admin", "Password")
DEMO_EMAIL = _cred("TEST_DEMO_EMAIL", "Demo Family", "Email")
DEMO_PASSWORD = _cred("TEST_DEMO_PASSWORD", "Demo Family", "Password")

ADMIN = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
DEMO = {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
