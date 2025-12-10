"""
Test audit logging functionality.
Ensures audit system works without breaking the main app.
"""
import sys
from pathlib import Path

# Add phase2/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "phase2" / "src"))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages_api.database import Base, AuditLog
from packages_api.audit import record_audit, query_audit_logs


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    db = TestSessionLocal()
    yield db
    db.close()


def test_record_audit_basic(test_db):
    """Test basic audit log recording"""
    record_audit(
        db=test_db,
        action="test.action",
        user_id="user123",
        resource="resource456",
        resource_type="test_resource",
        success=True,
        metadata={"key": "value"},
    )
    
    logs = test_db.query(AuditLog).all()
    assert len(logs) == 1
    
    log = logs[0]
    assert log.action == "test.action"
    assert log.user_id == "user123"
    assert log.resource == "resource456"
    assert log.resource_type == "test_resource"
    assert log.success is True
    assert log.metadata_json == {"key": "value"}
    assert log.created_at is not None


def test_record_audit_minimal(test_db):
    """Test audit recording with minimal fields"""
    record_audit(
        db=test_db,
        action="minimal.action",
    )
    
    logs = test_db.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].action == "minimal.action"
    assert logs[0].user_id is None
    assert logs[0].success is True


def test_query_audit_logs_no_filters(test_db):
    """Test querying all audit logs"""
    # Create test data
    record_audit(test_db, "action1", user_id="user1")
    record_audit(test_db, "action2", user_id="user2")
    record_audit(test_db, "action3", user_id="user1")
    
    logs = query_audit_logs(test_db)
    assert len(logs) == 3


def test_query_audit_logs_user_filter(test_db):
    """Test filtering by user_id"""
    record_audit(test_db, "action1", user_id="user1")
    record_audit(test_db, "action2", user_id="user2")
    record_audit(test_db, "action3", user_id="user1")
    
    logs = query_audit_logs(test_db, user_id="user1")
    assert len(logs) == 2
    assert all(log.user_id == "user1" for log in logs)


def test_query_audit_logs_action_filter(test_db):
    """Test filtering by action"""
    record_audit(test_db, "package.upload", user_id="user1")
    record_audit(test_db, "package.download", user_id="user2")
    record_audit(test_db, "package.upload", user_id="user3")
    
    logs = query_audit_logs(test_db, action="package.upload")
    assert len(logs) == 2
    assert all(log.action == "package.upload" for log in logs)


def test_query_audit_logs_limit(test_db):
    """Test limit parameter"""
    for i in range(20):
        record_audit(test_db, f"action{i}")
    
    logs = query_audit_logs(test_db, limit=5)
    assert len(logs) == 5


def test_query_audit_logs_time_range(test_db):
    """Test time range filtering"""
    now = datetime.utcnow()
    
    # This test is basic - just verify it doesn't crash
    logs = query_audit_logs(
        test_db,
        start=now - timedelta(hours=1),
        end=now + timedelta(hours=1),
    )
    # The query should work even if no results match
    assert isinstance(logs, list)


def test_record_audit_error_handling(test_db):
    """Test that audit errors don't break the app"""
    # Close the session to simulate DB error
    test_db.close()
    
    # This should not raise an exception
    record_audit(
        test_db,
        action="test.action",
        user_id="user123",
    )
    # No assertion needed - just verify it doesn't crash
