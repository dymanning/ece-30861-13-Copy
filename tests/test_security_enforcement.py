import os
import sys
import time
from pathlib import Path

import jwt as pyjwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Configure environment before importing the app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "phase2") not in sys.path:
    sys.path.insert(0, str(ROOT / "phase2"))

from src.packages_api import main as app_module  # noqa: E402
from src.packages_api.database import SessionLocal  # noqa: E402

client = TestClient(app_module.app)


def make_token(role: str = "user", sub: str = "user-1", secret: str = "test-secret") -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "exp": now + 3600,
        "iss": None,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def seed_artifact():
    session = SessionLocal()
    try:
        art = app_module.Artifact(id="seed-1", name="seed", artifact_type="model", url="https://example.com/a.zip")
        session.add(art)
        session.commit()
    finally:
        session.close()


def test_missing_token_rejected():
    resp = client.post("/artifacts", json=[{"name": "*"}])
    assert resp.status_code == 401


def test_invalid_token_rejected():
    bad_token = make_token(secret="wrong")
    resp = client.post(
        "/artifacts",
        headers={"Authorization": f"Bearer {bad_token}"},
        json=[{"name": "*"}],
    )
    assert resp.status_code == 401


def test_admin_required_for_delete():
    # Seed an artifact
    seed_artifact()
    user_token = make_token(role="user")
    resp = client.delete(
        "/artifacts/model/seed-1",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


def test_regex_length_limited():
    token = make_token()
    long_regex = "a" * 500
    resp = client.post(
        "/artifact/byRegEx",
        headers={"Authorization": f"Bearer {token}"},
        json={"regex": long_regex},
    )
    assert resp.status_code == 400
    assert "Regex too long" in resp.json().get("detail", "")
