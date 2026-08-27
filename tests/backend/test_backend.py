"""Backend unit tests: security, schemas, services (where SQLite-friendly)."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


class TestSecurity:
    def test_password_hash_and_verify(self):
        from app.core.security import hash_password, verify_password
        pw = "MySecret@123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)
        assert not verify_password("wrong", hashed)

    def test_jwt_create_and_decode(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token(user_id=42, role="citizen")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "citizen"
        assert payload["type"] == "access"

    def test_jwt_invalid_token(self):
        import jwt
        from app.core.security import decode_token
        with pytest.raises(jwt.PyJWTError):
            decode_token("invalid.token.here")


class TestSchemas:
    def test_user_create_validation(self):
        from app.schemas import UserCreate
        user = UserCreate(
            full_name="Jane Doe",
            email="jane@example.com",
            password="StrongP@ss1",
            role="citizen",
        )
        assert user.email == "jane@example.com"

    def test_user_create_rejects_weak_password(self):
        from pydantic import ValidationError
        from app.schemas import UserCreate
        with pytest.raises(ValidationError):
            UserCreate(
                full_name="Jane",
                email="jane@example.com",
                password="weakpassword",  # no uppercase, no digit
            )

    def test_user_create_rejects_admin_role(self):
        from pydantic import ValidationError
        from app.schemas import UserCreate
        with pytest.raises(ValidationError):
            UserCreate(
                full_name="Jane",
                email="jane@example.com",
                password="StrongP@ss1",
                role="admin",
            )

    def test_severity_update_validation(self):
        from app.schemas import SeverityUpdate
        s = SeverityUpdate(severity="Critical")
        assert s.severity == "Critical"

    def test_severity_update_rejects_invalid(self):
        from pydantic import ValidationError
        from app.schemas import SeverityUpdate
        with pytest.raises(ValidationError):
            SeverityUpdate(severity="Extreme")

    def test_verification_create_severity_vote(self):
        from app.schemas import VerificationCreate
        v = VerificationCreate(severity_vote="High", comment="Confirmed", is_confirmed=True)
        assert v.severity_vote == "High"

    def test_verification_create_rejects_invalid_severity(self):
        from pydantic import ValidationError
        from app.schemas import VerificationCreate
        with pytest.raises(ValidationError):
            VerificationCreate(severity_vote="Catastrophic")


class TestGeoUtils:
    def test_haversine(self):
        from app.utils.geo import haversine_km
        # Pune to Mumbai ~ 120 km
        d = haversine_km(18.5204, 73.8567, 19.0760, 72.8777)
        assert 100 < d < 150

    def test_haversine_zero(self):
        from app.utils.geo import haversine_km
        assert haversine_km(18.5, 73.8, 18.5, 73.8) == 0.0

    def test_make_point_wkt(self):
        from app.utils.geo import make_point_wkt
        wkt = make_point_wkt(18.52, 73.85)
        assert "POINT" in wkt
        assert "73.85" in wkt
        assert "18.52" in wkt


class TestHelpers:
    def test_generate_reference_code_format(self):
        # Import via service module
        from app.services.report_service import _generate_reference_code
        code = _generate_reference_code()
        assert code.startswith("RPT-")
        assert len(code.split("-")) == 3
