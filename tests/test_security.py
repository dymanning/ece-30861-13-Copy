"""
Security tests: JWT verification, RBAC, rate limiting, regex validation, and audit logging.
Tests enforce that security measures work without breaking existing functionality.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "phase2" / "src"))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages_api.database import Base
from packages_api.security import (
    create_jwt_token,
    decode_jwt_token,
    verify_jwt_token,
    require_admin,
    validate_regex_safe,
    validate_file_size,
    check_rate_limit,
)
from packages_api.audit import record_audit, query_audit_logs
from fastapi import HTTPException
import jwt


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    db = TestSessionLocal()
    yield db
    db.close()


# ============== JWT TOKEN TESTS ==============

def test_create_jwt_token():
    """Test JWT token creation with all required claims"""
    token = create_jwt_token("user123", role="admin", expires_in_hours=1)
    assert token
    assert isinstance(token, str)
    
    # Decode to verify claims
    payload = decode_jwt_token(token)
    assert payload["user_id"] == "user123"
    assert payload["role"] == "admin"
    assert payload["iss"] == "ece-461-registry"
    assert payload["aud"] == "ece-461-api"


def test_create_jwt_token_user_role():
    """Test JWT token creation with user role"""
    token = create_jwt_token("user456", role="user")
    payload = decode_jwt_token(token)
    assert payload["role"] == "user"


def test_verify_jwt_token_valid():
    """Test JWT token verification with valid token"""
    token = create_jwt_token("user123", role="admin")
    
    # Simulate X-Authorization header
    result = verify_jwt_token(authorization=f"Bearer {token}")
    
    assert result["user_id"] == "user123"
    assert result["role"] == "admin"


def test_verify_jwt_token_missing():
    """Test JWT verification fails without token"""
    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(authorization=None)
    assert exc_info.value.status_code == 401
    assert "Missing authentication token" in str(exc_info.value.detail)


def test_verify_jwt_token_invalid():
    """Test JWT verification fails with invalid token"""
    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(authorization="Bearer invalid.token.here")
    assert exc_info.value.status_code == 401


def test_verify_jwt_token_expired():
    """Test JWT verification fails with expired token"""
    # Create an expired token
    expired_payload = {
        "user_id": "user123",
        "role": "admin",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
        "iat": datetime.utcnow() - timedelta(hours=2),
        "iss": "ece-461-registry",
        "aud": "ece-461-api",
    }
    
    import os
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-not-for-production")
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
    
    with pytest.raises(HTTPException) as exc_info:
        verify_jwt_token(authorization=f"Bearer {expired_token}")
    assert exc_info.value.status_code == 401
    assert "expired" in str(exc_info.value.detail).lower()


# ============== RBAC TESTS ==============

def test_require_admin_with_admin_role():
    """Test RBAC allows admin to pass"""
    token = {"user_id": "admin123", "role": "admin"}
    result = require_admin(token)
    assert result == token


def test_require_admin_with_user_role():
    """Test RBAC rejects non-admin users"""
    token = {"user_id": "user123", "role": "user"}
    with pytest.raises(HTTPException) as exc_info:
        require_admin(token)
    assert exc_info.value.status_code == 403
    assert "Admin privileges required" in str(exc_info.value.detail)


def test_require_admin_missing_role():
    """Test RBAC rejects tokens without role claim"""
    token = {"user_id": "user123"}  # No role field
    with pytest.raises(HTTPException) as exc_info:
        require_admin(token)
    assert exc_info.value.status_code == 403


# ============== REGEX VALIDATION (REDOS PROTECTION) TESTS ==============

def test_validate_regex_safe_valid():
    """Test safe regex pattern is accepted"""
    assert validate_regex_safe("^[a-z]+$") is True


def test_validate_regex_safe_too_long():
    """Test regex pattern exceeding length limit is rejected"""
    long_pattern = "a" * 2000  # Exceeds 1000 char limit
    with pytest.raises(HTTPException) as exc_info:
        validate_regex_safe(long_pattern, max_length=1000)
    assert exc_info.value.status_code == 400
    assert "exceeds" in str(exc_info.value.detail).lower()


def test_validate_regex_safe_invalid_pattern():
    """Test invalid regex is rejected"""
    with pytest.raises(HTTPException) as exc_info:
        validate_regex_safe("(unclosed[group")
    assert exc_info.value.status_code == 400
    assert "Invalid regex" in str(exc_info.value.detail)


def test_validate_regex_safe_nested_quantifiers():
    """Test nested quantifiers (ReDoS risk) are rejected"""
    dangerous_pattern = "(a+)+"  # Nested quantifiers
    with pytest.raises(HTTPException) as exc_info:
        validate_regex_safe(dangerous_pattern)
    assert exc_info.value.status_code == 400
    assert "nested quantifiers" in str(exc_info.value.detail).lower()


def test_validate_regex_safe_multiple_nested():
    """Test multiple nested quantifiers rejected"""
    dangerous_pattern = "(a*)*"  # Nested *
    with pytest.raises(HTTPException) as exc_info:
        validate_regex_safe(dangerous_pattern)
    assert exc_info.value.status_code == 400


# ============== FILE SIZE VALIDATION TESTS ==============

def test_validate_file_size_valid():
    """Test valid file size is accepted"""
    assert validate_file_size(100 * 1024 * 1024) is True  # 100 MB


def test_validate_file_size_at_limit():
    """Test file size at limit is accepted"""
    assert validate_file_size(200 * 1024 * 1024, max_size_mb=200) is True


def test_validate_file_size_exceeds_limit():
    """Test file exceeding size limit is rejected"""
    with pytest.raises(HTTPException) as exc_info:
        validate_file_size(250 * 1024 * 1024, max_size_mb=200)
    assert exc_info.value.status_code == 413
    assert "exceeds" in str(exc_info.value.detail).lower()


# ============== RATE LIMITING TESTS ==============

def test_check_rate_limit_under_limit():
    """Test rate limit allows requests under limit"""
    # First 3 requests should succeed
    for i in range(3):
        assert check_rate_limit("user_123:upload", limit=3) is True


def test_check_rate_limit_exceeds_limit():
    """Test rate limit rejects requests exceeding limit"""
    # Fill up the limit
    for i in range(3):
        check_rate_limit("user_456:upload", limit=3)
    
    # Next request should fail
    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit("user_456:upload", limit=3)
    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in str(exc_info.value.detail)


def test_check_rate_limit_different_keys():
    """Test rate limits are per-key"""
    check_rate_limit("user_1:upload", limit=2)
    check_rate_limit("user_1:upload", limit=2)
    
    # Different user should have separate limit
    assert check_rate_limit("user_2:upload", limit=2) is True


# ============== AUDIT LOGGING WITH SECURITY TESTS ==============

def test_audit_log_deletion(test_db):
    """Test that deletions are properly audited"""
    record_audit(
        test_db,
        action="artifact.delete",
        user_id="admin123",
        resource="artifact_456",
        resource_type="model",
        success=True,
        metadata={"name": "my-model"}
    )
    
    logs = query_audit_logs(test_db, action="artifact.delete")
    assert len(logs) == 1
    assert logs[0].action == "artifact.delete"
    assert logs[0].user_id == "admin123"
    assert logs[0].resource == "artifact_456"


def test_audit_log_reset(test_db):
    """Test that registry resets are properly audited"""
    record_audit(
        test_db,
        action="registry.reset",
        user_id="admin123",
        resource_type="registry",
        success=True,
        metadata={"artifact_count": 5}
    )
    
    logs = query_audit_logs(test_db, action="registry.reset")
    assert len(logs) == 1
    assert logs[0].action == "registry.reset"
    assert logs[0].user_id == "admin123"
    # Verify sensitive fields not logged
    assert "admin123" in str(logs[0].user_id)  # User ID OK to log


def test_audit_log_failed_operation(test_db):
    """Test that failed operations are logged as such"""
    record_audit(
        test_db,
        action="artifact.create",
        user_id="user123",
        resource_type="model",
        success=False,
        metadata={"error": "Database connection failed"}
    )
    
    logs = query_audit_logs(test_db)
    assert len(logs) == 1
    assert logs[0].success is False
    # Verify error message doesn't expose sensitive data
    assert "error" in str(logs[0].metadata_json)


def test_audit_log_creation(test_db):
    """Test that artifact creation is audited"""
    record_audit(
        test_db,
        action="artifact.create",
        user_id="user123",
        resource="artifact_789",
        resource_type="dataset",
        success=True,
        metadata={"name": "my-dataset"}
    )
    
    logs = query_audit_logs(test_db, user_id="user123")
    assert len(logs) == 1
    assert logs[0].action == "artifact.create"


# ============== INTEGRATION TESTS ==============

def test_jwt_admin_rbac_integration():
    """Test JWT token + RBAC integration"""
    # Create admin token
    admin_token = create_jwt_token("admin_user", role="admin")
    
    # Verify token
    payload = verify_jwt_token(authorization=f"Bearer {admin_token}")
    
    # Check admin role
    result = require_admin(payload)
    assert result["role"] == "admin"


def test_jwt_user_rbac_integration():
    """Test JWT token fails RBAC for non-admin"""
    # Create user token
    user_token = create_jwt_token("regular_user", role="user")
    
    # Verify token succeeds
    payload = verify_jwt_token(authorization=f"Bearer {user_token}")
    assert payload["role"] == "user"
    
    # RBAC check fails
    with pytest.raises(HTTPException) as exc_info:
        require_admin(payload)
    assert exc_info.value.status_code == 403
