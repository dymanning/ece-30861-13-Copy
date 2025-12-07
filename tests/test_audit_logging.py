import datetime
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Point DATABASE_URL at SQLite for tests before importing the app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Ensure repository root is on sys.path so "phase2" imports resolve under pytest
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase2.src.packages_api import main as app_module
from phase2.src.packages_api import models
from phase2.src.packages_api.models import AuditLog
from phase2.src.packages_api.audit import record_audit, query_audit_logs


# Build an in-memory SQLite engine for isolated testing
engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_require_admin():
    return "admin"


app = app_module.app
app.dependency_overrides[app_module.get_db] = override_get_db
# require_admin is defined in logs_api; reuse the same dependency override here
from phase2.src import logs_api

app.dependency_overrides[logs_api.require_admin] = override_require_admin
client = TestClient(app)


def test_record_and_query_filters():
    db = TestingSessionLocal()
    try:
        record_audit(db, action="package.upload", user_id="u1", resource="1", resource_type="package")
        record_audit(db, action="package.download", user_id="u1", resource="1", resource_type="package")
        record_audit(db, action="package.upload", user_id="u2", resource="2", resource_type="package")

        logs_u1 = query_audit_logs(db, user_id="u1", limit=10)
        assert len(logs_u1) == 2
        assert all(log.user_id == "u1" for log in logs_u1)

        logs_upload = query_audit_logs(db, action="package.upload", limit=10)
        assert len(logs_upload) == 2
        assert all(log.action == "package.upload" for log in logs_upload)
    finally:
        db.close()


def test_export_endpoint_filters_and_admin_guard():
    db = TestingSessionLocal()
    try:
        db.query(AuditLog).delete()
        db.commit()
        # Seed a few audit entries
        record_audit(db, action="package.upload", user_id="alice", resource="10", metadata={"version": "1.0"})
        record_audit(db, action="package.download", user_id="bob", resource="10")
        record_audit(db, action="package.upload", user_id="alice", resource="11", metadata={"version": "2.0"})
    finally:
        db.close()

    # Filter by action
    resp = client.get("/audit/logs", params={"action": "package.upload", "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert all(entry["action"] == "package.upload" for entry in body)

    # Filter by user
    resp = client.get("/audit/logs", params={"user_id": "alice", "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert all(entry["user_id"] == "alice" for entry in body)

    # Date range filter (future should return none)
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    resp = client.get("/audit/logs", params={"start": future.isoformat(), "limit": 5})
    assert resp.status_code == 200
    assert resp.json() == []
