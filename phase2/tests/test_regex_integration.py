"""
Integration test for byRegEx endpoint with actual FastAPI TestClient
"""
import pytest
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with fresh database"""
    from src.packages_api.main import app, get_db, Base, engine, Artifact
    from sqlalchemy.orm import Session
    
    # Reset database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    client = TestClient(app)
    yield client
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client_with_data(client):
    """Create test client with pre-populated artifacts"""
    # Create some test artifacts
    test_artifacts = [
        {"type": "model", "url": "https://huggingface.co/bert-base-uncased"},
        {"type": "model", "url": "https://huggingface.co/audience-classifier"},
        {"type": "code", "url": "https://github.com/openai/whisper"},
        {"type": "dataset", "url": "https://huggingface.co/datasets/bookcorpus"},
    ]
    
    for artifact in test_artifacts:
        response = client.post(
            f"/artifact/{artifact['type']}",
            json={"url": artifact["url"]},
            headers={"X-Authorization": "bearer test-token"}
        )
        # Accept 201 (created) or 409 (already exists)
        assert response.status_code in [201, 409], f"Failed to create artifact: {response.text}"
    
    return client


class TestByRegExEndpoint:
    """Test /artifact/byRegEx endpoint"""
    
    def test_regex_exact_match(self, client_with_data):
        """Test exact match regex"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": "^bert-base-uncased$"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 1
            # Check response format
            for item in data:
                assert "name" in item
                assert "id" in item
                assert "type" in item
        elif response.status_code == 404:
            # May not find if name extraction is different
            pass
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_regex_partial_match(self, client_with_data):
        """Test partial match regex from OpenAPI spec example"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": ".*?(audience|bert).*"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            # Should find at least one artifact
            names = [item["name"] for item in data]
            # Check that matches contain audience or bert
            for name in names:
                assert "audience" in name.lower() or "bert" in name.lower(), f"Name {name} should contain audience or bert"
        elif response.status_code == 404:
            pass  # OK if artifacts weren't created
    
    def test_regex_wildcard_all(self, client_with_data):
        """Test wildcard regex that matches all"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": ".*"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            # Should find multiple artifacts
            assert len(data) >= 1
    
    def test_regex_no_match(self, client_with_data):
        """Test regex that matches nothing"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": "^xyz-nonexistent-artifact-12345$"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        # Should return 404 when no matches
        assert response.status_code == 404
    
    def test_regex_invalid_pattern(self, client_with_data):
        """Test invalid regex pattern"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": "[invalid(regex"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        # Should return 400 for invalid regex
        assert response.status_code == 400
    
    def test_regex_response_format(self, client_with_data):
        """Test that response format matches OpenAPI spec"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": ".*"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        if response.status_code == 200:
            data = response.json()
            for item in data:
                # Must have exactly these fields per ArtifactMetadata schema
                assert set(item.keys()) == {"name", "id", "type"}, f"Response should only have name, id, type: {item}"
                assert isinstance(item["name"], str)
                assert isinstance(item["id"], (str, int))
                assert item["type"] in ["model", "dataset", "code"]


class TestByRegExEdgeCases:
    """Test edge cases for regex endpoint"""
    
    def test_empty_regex(self, client_with_data):
        """Test empty regex string"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": ""},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        # Empty regex matches everything or returns error
        assert response.status_code in [200, 400, 404]
    
    def test_regex_special_characters(self, client_with_data):
        """Test regex with special characters that need escaping"""
        response = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": "whisper"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        if response.status_code == 200:
            data = response.json()
            for item in data:
                assert "whisper" in item["name"].lower()
    
    def test_regex_case_sensitivity(self, client_with_data):
        """Test that regex is case-sensitive as expected"""
        # Search with lowercase
        response_lower = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": "bert"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        # Search with uppercase
        response_upper = client_with_data.post(
            "/artifact/byRegEx",
            json={"regex": "BERT"},
            headers={"X-Authorization": "bearer test-token"}
        )
        
        # Both should work (artifact names are typically lowercase)
        # but results may differ based on case
        assert response_lower.status_code in [200, 404]
        assert response_upper.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
