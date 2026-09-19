"""Seed-credential security: env-driven, fail-safe when absent, no demo user in production, nothing printed."""
import os
import sys
import importlib
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEED_KEYS = ("SEED_ADMIN_EMAIL", "SEED_ADMIN_PASSWORD", "SEED_ADMIN_FAMILY_NAME", "SEED_DEMO_ENABLED",
             "SEED_DEMO_EMAIL", "SEED_DEMO_PASSWORD", "APP_ENV", "STRIPE_MODE")


@pytest.fixture
def seed(monkeypatch):
    for k in SEED_KEYS: monkeypatch.delenv(k, raising=False)
    import seed as mod
    return importlib.reload(mod)


def test_admin_requires_env(seed):
    with pytest.raises(SystemExit, match="SEED_ADMIN_PASSWORD"):
        seed.build_admin()
    os.environ["SEED_ADMIN_PASSWORD"] = "a-very-strong-passphrase-2026"
    with pytest.raises(SystemExit, match="SEED_ADMIN_EMAIL"):
        seed.build_admin()


def test_admin_password_min_length(seed, monkeypatch):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "short")
    with pytest.raises(SystemExit, match="12 characters"):
        seed.build_admin()


def test_admin_built_from_env_and_hashed(seed, monkeypatch):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "Owner@Example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "a-very-strong-passphrase-2026")
    a = seed.build_admin()
    assert a["email"] == "owner@example.com" and a["role"] == "admin"
    assert a["password_hash"].startswith("$2") and "a-very-strong-passphrase-2026" not in str(a)
    import bcrypt
    assert bcrypt.checkpw(b"a-very-strong-passphrase-2026", a["password_hash"].encode())


def test_demo_disabled_by_default_and_in_production(seed, monkeypatch):
    assert seed.demo_enabled() is False
    monkeypatch.setenv("SEED_DEMO_ENABLED", "true")
    assert seed.demo_enabled() is True
    monkeypatch.setenv("APP_ENV", "production")
    assert seed.demo_enabled() is False
    monkeypatch.delenv("APP_ENV"); monkeypatch.setenv("STRIPE_MODE", "live")
    assert seed.demo_enabled() is False


def test_demo_requires_env_when_enabled(seed, monkeypatch):
    monkeypatch.setenv("SEED_DEMO_ENABLED", "true")
    with pytest.raises(SystemExit, match="SEED_DEMO_PASSWORD"):
        seed.build_demo()


def test_no_hardcoded_passwords_in_tracked_sources():
    import subprocess
    root = Path(__file__).resolve().parents[2]
    out = subprocess.run(["git", "grep", "-n", "-I", "-E", r"(JeanaAdmin|DemoFamily)[0-9]+!"], cwd=root, capture_output=True, text=True)
    assert out.returncode == 1 and out.stdout == "", f"credential values found in tracked files:\n{out.stdout}"
    src = (root / "backend" / "seed.py").read_text()
    assert 'h("' not in src  # no literal password passed to the hasher
