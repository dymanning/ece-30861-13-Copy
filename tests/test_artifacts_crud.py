"""
Artifact CRUD Tests
Tests CREATE, READ, UPDATE, DELETE operations for artifacts API
Validates that rating, cost, dependencies, uri, and size fields are properly stored and retrieved
"""
import pytest
import requests
import json


class TestArtifactCreate:
    """Test POST /artifacts/{type} - Create artifact"""
    
    @pytest.mark.usefixtures("typescript_server")
    def test_create_model_artifact(self, typescript_server_url, auth_headers, db_session):
        """Test creating a new model artifact with all fields populated"""
        from sqlalchemy import text
        
        # Prepare artifact data
        artifact_data = {
            "data": {
                "url": "https://huggingface.co/test-org/test-create-model"
            }
        }
        
        response = requests.post(
            f"{typescript_server_url}/artifacts/model",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=artifact_data
        )
        
        # Validate response
        assert response.status_code == 201, (
            f"Expected 201 Created but got {response.status_code}. "
            f"Response body: {response.text}"
        )
        
        data = response.json()
        assert "metadata" in data, f"Response missing 'metadata' field. Got: {data}"
        assert "id" in data["metadata"], f"Response metadata missing 'id'. Got: {data['metadata']}"
        assert "name" in data["metadata"], f"Response metadata missing 'name'. Got: {data['metadata']}"
        assert data["metadata"]["type"] == "model", (
            f"Expected type='model' but got '{data['metadata']['type']}'"
        )
        
        artifact_id = data["metadata"]["id"]
        
        # Verify artifact was stored in database with all fields
        result = db_session.execute(text("""
            SELECT id, name, type, url, uri, size, rating, cost, dependencies
            FROM artifacts 
            WHERE id = :id
        """), {"id": artifact_id})
        
        row = result.fetchone()
        assert row is not None, (
            f"Artifact with id={artifact_id} not found in database after creation. "
            f"CREATE operation failed to persist artifact."
        )
        
        db_id, db_name, db_type, db_url, db_uri, db_size, db_rating, db_cost, db_dependencies = row
        
        # Validate database fields
        assert db_type == "model", f"Database type mismatch: expected 'model', got '{db_type}'"
        assert db_url == "https://huggingface.co/test-org/test-create-model", (
            f"Database URL mismatch: expected 'https://huggingface.co/test-org/test-create-model', "
            f"got '{db_url}'"
        )
        assert db_uri is not None and db_uri.startswith("s3://"), (
            f"Database URI should be S3 path starting with 's3://', got: {db_uri}"
        )
        assert db_size is not None and db_size > 0, (
            f"Database size should be positive integer (bytes), got: {db_size}"
        )
        assert db_rating is not None, f"Database rating field is NULL, should contain JSON object"
        assert db_cost is not None, f"Database cost field is NULL, should contain JSON object"
        
        # Parse JSON fields
        try:
            rating = json.loads(db_rating) if isinstance(db_rating, str) else db_rating
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse rating JSON from database: {e}. Value: {db_rating}")
        
        try:
            cost = json.loads(db_cost) if isinstance(db_cost, str) else db_cost
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse cost JSON from database: {e}. Value: {db_cost}")
        
        # Validate rating structure
        assert "quality" in rating, f"Rating missing 'quality' field. Got: {rating}"
        assert "size_score" in rating, f"Rating missing 'size_score' field. Got: {rating}"
        assert "code_quality" in rating, f"Rating missing 'code_quality' field. Got: {rating}"
        assert "bus_factor" in rating, f"Rating missing 'bus_factor' field. Got: {rating}"
        
        # Validate cost structure
        assert "inference_cents" in cost or "storage" in cost, (
            f"Cost should have 'inference_cents' or 'storage' field. Got: {cost}"
        )
        
        # Cleanup
        db_session.execute(text("DELETE FROM artifacts WHERE id = :id"), {"id": artifact_id})
        db_session.commit()
    
    @pytest.mark.usefixtures("typescript_server")
    def test_create_dataset_artifact(self, typescript_server_url, auth_headers, db_session):
        """Test creating a dataset artifact"""
        from sqlalchemy import text
        
        artifact_data = {
            "data": {
                "url": "https://huggingface.co/datasets/test-dataset"
            }
        }
        
        response = requests.post(
            f"{typescript_server_url}/artifacts/dataset",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=artifact_data
        )
        
        assert response.status_code == 201, (
            f"Expected 201 Created for dataset but got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        data = response.json()
        assert data["metadata"]["type"] == "dataset", (
            f"Expected type='dataset' but got '{data['metadata']['type']}'"
        )
        
        # Cleanup
        artifact_id = data["metadata"]["id"]
        db_session.execute(text("DELETE FROM artifacts WHERE id = :id"), {"id": artifact_id})
        db_session.commit()
    
    @pytest.mark.usefixtures("typescript_server")
    def test_create_code_artifact(self, typescript_server_url, auth_headers, db_session):
        """Test creating a code artifact"""
        from sqlalchemy import text
        
        artifact_data = {
            "data": {
                "url": "https://github.com/test-org/test-repo"
            }
        }
        
        response = requests.post(
            f"{typescript_server_url}/artifacts/code",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=artifact_data
        )
        
        assert response.status_code == 201, (
            f"Expected 201 Created for code artifact but got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        data = response.json()
        assert data["metadata"]["type"] == "code", (
            f"Expected type='code' but got '{data['metadata']['type']}'"
        )
        
        # Cleanup
        artifact_id = data["metadata"]["id"]
        db_session.execute(text("DELETE FROM artifacts WHERE id = :id"), {"id": artifact_id})
        db_session.commit()
    
    @pytest.mark.usefixtures("typescript_server")
    def test_create_duplicate_artifact_fails(self, typescript_server_url, auth_headers, db_session):
        """Test that creating duplicate artifact returns 409 Conflict"""
        from sqlalchemy import text
        
        artifact_data = {
            "metadata": {
                "id": "test-duplicate-12345"
            },
            "data": {
                "url": "https://example.com/duplicate-test"
            }
        }
        
        # Create first artifact
        response1 = requests.post(
            f"{typescript_server_url}/artifacts/model",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=artifact_data
        )
        
        if response1.status_code != 201:
            pytest.skip(f"First creation failed with {response1.status_code}, cannot test duplicate")
        
        # Attempt to create duplicate
        response2 = requests.post(
            f"{typescript_server_url}/artifacts/model",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=artifact_data
        )
        
        assert response2.status_code == 409, (
            f"Expected 409 Conflict when creating duplicate artifact, "
            f"but got {response2.status_code}. Response: {response2.text}"
        )
        
        # Cleanup
        db_session.execute(text("DELETE FROM artifacts WHERE id = :id"), 
                          {"id": "test-duplicate-12345"})
        db_session.commit()


class TestArtifactRead:
    """Test GET /artifacts/{type}/{id} - Read artifact"""
    
    @pytest.mark.usefixtures("typescript_server", "sample_artifacts")
    def test_get_existing_artifact(self, typescript_server_url, auth_headers):
        """Test retrieving an existing artifact with all fields"""
        response = requests.get(
            f"{typescript_server_url}/artifacts/model/test-bert-1",
            headers=auth_headers
        )
        
        assert response.status_code == 200, (
            f"Expected 200 OK when getting existing artifact, but got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        data = response.json()
        
        # Validate core fields
        assert "id" in data, f"Response missing 'id' field. Got: {data}"
        assert data["id"] == "test-bert-1", (
            f"ID mismatch: expected 'test-bert-1', got '{data['id']}'"
        )
        assert "name" in data, f"Response missing 'name' field. Got: {data}"
        assert "type" in data, f"Response missing 'type' field. Got: {data}"
        assert data["type"] == "model", f"Type mismatch: expected 'model', got '{data['type']}'"
        
        # Validate metadata fields
        assert "metadata" in data, f"Response missing 'metadata' field. Got: {data}"
        metadata = data["metadata"]
        assert "url" in metadata, f"Metadata missing 'url' field. Got: {metadata}"
        
        # Validate new fields (should be present even if default/stub values)
        assert "uri" in data, f"Response missing 'uri' field. Got: {data}"
        assert "size" in data, f"Response missing 'size' field. Got: {data}"
        assert "rating" in data, f"Response missing 'rating' field. Got: {data}"
        assert "cost" in data, f"Response missing 'cost' field. Got: {data}"
        assert "dependencies" in data, f"Response missing 'dependencies' field. Got: {data}"
        
        # Validate rating structure
        rating = data["rating"]
        assert isinstance(rating, dict), f"Rating should be dict/object, got {type(rating)}"
        assert "quality" in rating, f"Rating missing 'quality'. Got: {rating}"
        assert "size_score" in rating, f"Rating missing 'size_score'. Got: {rating}"
        assert "code_quality" in rating, f"Rating missing 'code_quality'. Got: {rating}"
        assert "bus_factor" in rating, f"Rating missing 'bus_factor'. Got: {rating}"
        
        # Validate cost structure
        cost = data["cost"]
        assert isinstance(cost, dict), f"Cost should be dict/object, got {type(cost)}"
        
        # Validate dependencies is array
        dependencies = data["dependencies"]
        assert isinstance(dependencies, list), (
            f"Dependencies should be array/list, got {type(dependencies)}"
        )
    
    @pytest.mark.usefixtures("typescript_server")
    def test_get_nonexistent_artifact(self, typescript_server_url, auth_headers):
        """Test retrieving non-existent artifact returns 404"""
        response = requests.get(
            f"{typescript_server_url}/artifacts/model/nonexistent-id-99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404, (
            f"Expected 404 Not Found for non-existent artifact, but got {response.status_code}. "
            f"Response: {response.text}"
        )
    
    @pytest.mark.usefixtures("typescript_server", "sample_artifacts")
    def test_get_artifact_wrong_type(self, typescript_server_url, auth_headers):
        """Test retrieving artifact with wrong type returns 404"""
        # test-bert-1 is a model, try to get it as dataset
        response = requests.get(
            f"{typescript_server_url}/artifacts/dataset/test-bert-1",
            headers=auth_headers
        )
        
        assert response.status_code == 404, (
            f"Expected 404 when accessing artifact with wrong type, "
            f"but got {response.status_code}. Response: {response.text}"
        )


class TestArtifactUpdate:
    """Test PUT /artifacts/{type}/{id} - Update artifact"""
    
    @pytest.mark.usefixtures("typescript_server", "sample_artifacts")
    def test_update_artifact_url(self, typescript_server_url, auth_headers, db_session):
        """Test updating artifact URL and verify metrics are recomputed"""
        from sqlalchemy import text
        
        artifact_id = "test-bert-1"
        
        # Get original artifact
        response_before = requests.get(
            f"{typescript_server_url}/artifacts/model/{artifact_id}",
            headers=auth_headers
        )
        assert response_before.status_code == 200, "Setup failed: artifact doesn't exist"
        original_data = response_before.json()
        
        # Update artifact
        update_data = {
            "data": {
                "url": "https://huggingface.co/updated-org/updated-model"
            }
        }
        
        response = requests.put(
            f"{typescript_server_url}/artifacts/model/{artifact_id}",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=update_data
        )
        
        assert response.status_code == 200, (
            f"Expected 200 OK when updating artifact, but got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        # Verify update was persisted
        result = db_session.execute(text("""
            SELECT url, rating, cost, updated_at
            FROM artifacts 
            WHERE id = :id
        """), {"id": artifact_id})
        
        row = result.fetchone()
        assert row is not None, f"Artifact {artifact_id} disappeared after update"
        
        db_url, db_rating, db_cost, db_updated = row
        
        assert db_url == "https://huggingface.co/updated-org/updated-model", (
            f"URL not updated in database. Expected new URL, got: {db_url}"
        )
        
        # Verify metrics were recomputed (rating/cost should be present)
        assert db_rating is not None, (
            "Rating should be recomputed on update, but got NULL in database"
        )
        assert db_cost is not None, (
            "Cost should be recomputed on update, but got NULL in database"
        )
    
    @pytest.mark.usefixtures("typescript_server")
    def test_update_nonexistent_artifact(self, typescript_server_url, auth_headers):
        """Test updating non-existent artifact returns 404"""
        update_data = {
            "data": {
                "url": "https://example.com/new-url"
            }
        }
        
        response = requests.put(
            f"{typescript_server_url}/artifacts/model/nonexistent-id-99999",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=update_data
        )
        
        assert response.status_code == 404, (
            f"Expected 404 Not Found when updating non-existent artifact, "
            f"but got {response.status_code}. Response: {response.text}"
        )


class TestArtifactDelete:
    """Test DELETE /artifacts/{type}/{id} - Delete artifact"""
    
    @pytest.mark.usefixtures("typescript_server")
    def test_delete_artifact(self, typescript_server_url, auth_headers, db_session):
        """Test deleting an artifact"""
        from sqlalchemy import text
        
        # Create artifact to delete
        artifact_data = {
            "metadata": {
                "id": "test-to-delete-123"
            },
            "data": {
                "url": "https://example.com/to-delete"
            }
        }
        
        create_response = requests.post(
            f"{typescript_server_url}/artifacts/model",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=artifact_data
        )
        
        if create_response.status_code != 201:
            pytest.skip(f"Setup failed: couldn't create artifact. Got {create_response.status_code}")
        
        # Delete artifact
        response = requests.delete(
            f"{typescript_server_url}/artifacts/model/test-to-delete-123",
            headers=auth_headers
        )
        
        assert response.status_code == 204, (
            f"Expected 204 No Content when deleting artifact, "
            f"but got {response.status_code}. Response: {response.text}"
        )
        
        # Verify artifact was deleted from database
        result = db_session.execute(text("""
            SELECT id FROM artifacts WHERE id = :id
        """), {"id": "test-to-delete-123"})
        
        row = result.fetchone()
        assert row is None, (
            f"Artifact with id='test-to-delete-123' still exists in database after DELETE. "
            f"DELETE operation failed to remove artifact."
        )
    
    @pytest.mark.usefixtures("typescript_server")
    def test_delete_nonexistent_artifact(self, typescript_server_url, auth_headers):
        """Test deleting non-existent artifact returns 404"""
        response = requests.delete(
            f"{typescript_server_url}/artifacts/model/nonexistent-id-99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404, (
            f"Expected 404 Not Found when deleting non-existent artifact, "
            f"but got {response.status_code}. Response: {response.text}"
        )


class TestModelRating:
    """Test GET /artifact/model/{id}/rate - Get model rating"""
    
    @pytest.mark.usefixtures("typescript_server", "sample_artifacts")
    def test_get_model_rating(self, typescript_server_url, auth_headers):
        """Test retrieving model rating with phase1 metrics"""
        response = requests.get(
            f"{typescript_server_url}/artifact/model/test-bert-1/rate",
            headers=auth_headers
        )
        
        assert response.status_code == 200, (
            f"Expected 200 OK when getting model rating, but got {response.status_code}. "
            f"Response: {response.text}"
        )
        
        data = response.json()
        
        # Validate rating structure matches RatingMetrics interface
        assert "quality" in data, f"Rating missing 'quality' field. Got: {data}"
        assert "size_score" in data, f"Rating missing 'size_score' field. Got: {data}"
        assert "code_quality" in data, f"Rating missing 'code_quality' field. Got: {data}"
        assert "dataset_quality" in data, f"Rating missing 'dataset_quality' field. Got: {data}"
        assert "performance_claims" in data, f"Rating missing 'performance_claims' field. Got: {data}"
        assert "bus_factor" in data, f"Rating missing 'bus_factor' field. Got: {data}"
        assert "ramp_up_time" in data, f"Rating missing 'ramp_up_time' field. Got: {data}"
        assert "dataset_and_code_score" in data, f"Rating missing 'dataset_and_code_score' field. Got: {data}"
        
        # Validate size_score structure (should be object with device scores)
        size_score = data["size_score"]
        assert isinstance(size_score, dict), (
            f"size_score should be object/dict, got {type(size_score)}"
        )
        assert "raspberry_pi" in size_score, f"size_score missing 'raspberry_pi'. Got: {size_score}"
        assert "jetson_nano" in size_score, f"size_score missing 'jetson_nano'. Got: {size_score}"
        assert "desktop_pc" in size_score, f"size_score missing 'desktop_pc'. Got: {size_score}"
        assert "aws_server" in size_score, f"size_score missing 'aws_server'. Got: {size_score}"
        
        # Validate numeric ranges
        assert 0 <= data["quality"] <= 1, (
            f"quality should be in range [0, 1], got {data['quality']}"
        )
        assert isinstance(data["bus_factor"], (int, float)), (
            f"bus_factor should be numeric, got {type(data['bus_factor'])}"
        )
    
    @pytest.mark.usefixtures("typescript_server")
    def test_get_rating_for_nonexistent_model(self, typescript_server_url, auth_headers):
        """Test getting rating for non-existent model returns 404"""
        response = requests.get(
            f"{typescript_server_url}/artifact/model/nonexistent-id-99999/rate",
            headers=auth_headers
        )
        
        assert response.status_code == 404, (
            f"Expected 404 Not Found for non-existent model rating, "
            f"but got {response.status_code}. Response: {response.text}"
        )


class TestArtifactFieldValidation:
    """Test that all expected fields are properly populated and validated"""
    
    @pytest.mark.usefixtures("typescript_server")
    def test_created_artifact_has_all_fields(self, typescript_server_url, auth_headers, db_session):
        """Test that newly created artifact has uri, size, rating, cost, dependencies"""
        from sqlalchemy import text
        
        artifact_data = {
            "data": {
                "url": "https://huggingface.co/test-validation/model"
            }
        }
        
        # Create artifact
        create_response = requests.post(
            f"{typescript_server_url}/artifacts/model",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=artifact_data
        )
        
        assert create_response.status_code == 201, f"Setup failed: {create_response.text}"
        artifact_id = create_response.json()["metadata"]["id"]
        
        # Get artifact
        get_response = requests.get(
            f"{typescript_server_url}/artifacts/model/{artifact_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200, f"Failed to retrieve created artifact"
        data = get_response.json()
        
        # Comprehensive field validation
        required_fields = ["id", "name", "type", "metadata", "uri", "size", "rating", "cost", "dependencies"]
        for field in required_fields:
            assert field in data, (
                f"Created artifact missing required field '{field}'. "
                f"Available fields: {list(data.keys())}"
            )
        
        # Type validation
        assert isinstance(data["uri"], str), f"uri should be string, got {type(data['uri'])}"
        assert isinstance(data["size"], int), f"size should be integer, got {type(data['size'])}"
        assert isinstance(data["rating"], dict), f"rating should be object, got {type(data['rating'])}"
        assert isinstance(data["cost"], dict), f"cost should be object, got {type(data['cost'])}"
        assert isinstance(data["dependencies"], list), f"dependencies should be array, got {type(data['dependencies'])}"
        
        # Value validation
        assert data["uri"].startswith("s3://"), f"uri should be S3 path, got: {data['uri']}"
        assert data["size"] > 0, f"size should be positive, got: {data['size']}"
        
        # Cleanup
        db_session.execute(text("DELETE FROM artifacts WHERE id = :id"), {"id": artifact_id})
        db_session.commit()
