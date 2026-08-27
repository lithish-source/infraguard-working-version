"""Test configuration: SQLite in-memory + clean settings.

Sets up environment for backend tests; AI tests do not depend on this.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Set env vars BEFORE importing anything from app.*
# Force override (not setdefault) — system env may have a different DATABASE_URL
os.environ["DATABASE_URL"] = "sqlite:///./test_infraguard.db"
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_for_pytest")
os.environ.setdefault("UPLOAD_DIR", "./test_uploads")
os.environ.setdefault("DEBUG", "true")

# Patch geoalchemy2 for SQLite tests
import sys as _sys
import sqlalchemy as _sa
from sqlalchemy.types import TypeDecorator


class _DummyGeom(TypeDecorator):
    impl = _sa.Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        # Accept and discard geometry_type, srid, etc.
        super().__init__()


if "geoalchemy2" in _sys.modules:
    import geoalchemy2 as _gad
    _gad.Geometry = _DummyGeom
else:
    class _FakeGA:
        Geometry = _DummyGeom
    _sys.modules["geoalchemy2"] = _FakeGA()


import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_payload():
    return {
        "full_name": "Test Citizen",
        "email": "test@example.com",
        "phone": "+919999999999",
        "password": "Test@12345",
        "role": "citizen",
    }
