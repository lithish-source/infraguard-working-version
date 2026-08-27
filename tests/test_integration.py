"""Integration test stub — full stack smoke test.

Requires running backend on localhost:8000. Skipped otherwise.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

httpx = pytest.importorskip("httpx")


BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _backend_reachable() -> bool:
    """Check if the InfraGuard backend is actually running on BASE_URL.

    Returns True only if we get a response that looks like our backend
    (i.e. the root endpoint returns the expected app name).
    """
    try:
        r = httpx.get(f"{BASE_URL}/", timeout=5)
        data = r.json()
        return r.status_code == 200 and data.get("app") == "InfraGuard"
    except Exception:
        return False


@pytest.fixture(autouse=True)
def require_backend():
    """Automatically skip every test in this module if the backend is not running."""
    if not _backend_reachable():
        pytest.skip("InfraGuard backend not running on " + BASE_URL)


def test_health_endpoint():
    r = httpx.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"


def test_openapi_docs_available():
    r = httpx.get(f"{BASE_URL}/api/v1/openapi.json", timeout=5)
    assert r.status_code == 200
    spec = r.json()
    assert "paths" in spec
    # Sanity check: must have auth endpoints
    assert "/api/v1/auth/login" in spec["paths"]
    assert "/api/v1/reports" in spec["paths"]


def test_admin_login_works():
    """If backend seeded, admin login should succeed."""
    r = httpx.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@infraguard.gov", "password": "Admin@12345"},
        timeout=5,
    )
    if r.status_code == 401:
        pytest.skip("Backend not seeded yet")
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"
