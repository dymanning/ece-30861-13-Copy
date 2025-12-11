"""
Pytest configuration and shared fixtures for all tests
"""
import os
import sys
import pytest
import subprocess
import time
import requests
from pathlib import Path

# Add phase2/src to Python path for imports
PHASE2_SRC = Path(__file__).parent.parent / "phase2" / "src"
sys.path.insert(0, str(PHASE2_SRC))


@pytest.fixture(scope="session")
def database_url():
    """Database connection URL"""
    return os.getenv(
        "DATABASE_URL",
        "sqlite:///./test_artifact_registry.db"
    )


@pytest.fixture(scope="session")
def typescript_server_url():
    """TypeScript Node.js server URL"""
    return os.getenv("TYPESCRIPT_SERVER_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def fastapi_server_url():
    """FastAPI Python server URL"""
    return os.getenv("FASTAPI_SERVER_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def typescript_server(typescript_server_url):
    """
    Start TypeScript Node.js server for tests
    Assumes server is already running or will be started externally
    """
    # Check if server is already running
    try:
        response = requests.get(f"{typescript_server_url}/health", timeout=2)
        if response.status_code == 200:
            yield typescript_server_url
            return
    except requests.exceptions.RequestException:
        pass
    
    # If not running, skip tests that need it
    pytest.skip("TypeScript server not running. Start with: npm start")


@pytest.fixture(scope="session")
def fastapi_server(fastapi_server_url, database_url):
    """
    Start FastAPI server for tests
    Assumes server is already running or will be started externally
    """
    # Check if server is already running
    try:
        response = requests.get(f"{fastapi_server_url}/docs", timeout=2)
        if response.status_code == 200:
            yield fastapi_server_url
            return
    except requests.exceptions.RequestException:
        pass
    
    # If not running, skip tests that need it
    pytest.skip("FastAPI server not running. Start with: uvicorn main:app")


@pytest.fixture
def auth_headers():
    """
    Authentication headers for API requests
    Uses dummy token for testing
    """
    return {
        "X-Authorization": "bearer test-token-12345"
    }


@pytest.fixture
def db_session(database_url):
    """
    Database session for direct DB tests
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def clean_monitoring_history(db_session):
    """
    Clean monitoring_history table before test
    """
    from sqlalchemy import text
    
    db_session.execute(text("DELETE FROM monitoring_history"))
    db_session.commit()
    yield
    # Cleanup after test
    db_session.execute(text("DELETE FROM monitoring_history"))
    db_session.commit()


@pytest.fixture
def sample_packages(db_session):
    """
    Create sample packages for testing
    """
    from sqlalchemy import text
    
    # Clean existing test packages
    db_session.execute(text("DELETE FROM packages WHERE name LIKE 'test-%'"))
    db_session.commit()
    
    # Insert test packages
    packages = [
        ("test-safe-model", "model", True, "default-check.js"),
        ("test-malware-backdoor", "model", True, "default-check.js"),
        ("test-normal-code", "code", False, None),
    ]
    
    for name, type_, is_sensitive, script in packages:
        db_session.execute(text("""
            INSERT INTO packages (name, type, s3_uri, is_sensitive, monitoring_script)
            VALUES (:name, :type, :s3_uri, :is_sensitive, :script)
            ON CONFLICT (name) DO UPDATE 
            SET is_sensitive = EXCLUDED.is_sensitive,
                monitoring_script = EXCLUDED.monitoring_script
        """), {
            "name": name,
            "type": type_,
            "s3_uri": f"s3://bucket/{name}.zip",
            "is_sensitive": is_sensitive,
            "script": script
        })
    
    db_session.commit()
    
    yield
    
    # Cleanup
    db_session.execute(text("DELETE FROM packages WHERE name LIKE 'test-%'"))
    db_session.commit()


@pytest.fixture
def sample_artifacts(db_session):
    """
    Create sample artifacts for TypeScript API testing
    """
    from sqlalchemy import text
    
    # Clean existing test artifacts
    db_session.execute(text("DELETE FROM artifacts WHERE id LIKE 'test-%'"))
    db_session.commit()
    
    # Insert test artifacts with explicit IDs
    artifacts = [
        ("test-bert-1", "test-bert-model", "model", "https://example.com/bert.zip", "BERT base model for NLP"),
        ("test-gpt-2", "test-gpt-model", "model", "https://example.com/gpt.zip", "GPT model for text generation"),
        ("test-imagenet-3", "test-dataset-imagenet", "dataset", "https://example.com/imagenet.zip", "ImageNet dataset"),
        ("test-malware-4", "test-malware-detector", "code", "https://example.com/malware.zip", "Malware detection code"),
        ("test-virus-5", "test-virus-scanner", "code", "https://example.com/virus.zip", "Virus scanning utility"),
    ]
    
    for artifact_id, name, type_, url, readme in artifacts:
        # Insert new artifact with explicit id
        db_session.execute(text("""
            INSERT INTO artifacts (id, name, type, url, readme)
            VALUES (:id, :name, :type, :url, :readme)
            ON CONFLICT (id) DO UPDATE 
            SET name = EXCLUDED.name,
                type = EXCLUDED.type,
                url = EXCLUDED.url,
                readme = EXCLUDED.readme
        """), {
            "id": artifact_id,
            "name": name,
            "type": type_,
            "url": url,
            "readme": readme
        })
    
    db_session.commit()
    
    yield
    
    # Cleanup
    db_session.execute(text("DELETE FROM artifacts WHERE name LIKE 'test-%'"))
    db_session.commit()
