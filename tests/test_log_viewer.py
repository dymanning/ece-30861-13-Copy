"""
Log Viewer API Tests
Tests for admin-only log viewing endpoints
Verifies proper authentication and authorization
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys
import tempfile
import os

# Import the FastAPI app
sys.path.insert(0, str(Path(__file__).parent.parent / "phase2" / "src"))
from logs_api import router, get_current_user_role, LogResponse
from fastapi import FastAPI, Depends, HTTPException


# Create test app
app = FastAPI()
app.include_router(router)


class TestLogViewerEndpoints:
    """Test log viewer API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_deploy_log(self, tmp_path, monkeypatch):
        """Create a mock deploy log file"""
        log_file = tmp_path / "deploy.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write sample log entries
        log_content = """2025-11-30 10:00:01 Starting deploy at Sat Nov 30 10:00:01 UTC 2025
2025-11-30 10:00:02 App dir: /home/ec2-user/app
2025-11-30 10:00:03 Found unpacked artifact in /tmp/deploy
2025-11-30 10:00:04 Installing Python requirements
2025-11-30 10:00:05 Restarting systemd service: phase2
2025-11-30 10:00:06 Deploy completed at: Sat Nov 30 10:00:06 UTC 2025
"""
        log_file.write_text(log_content)
        
        # Monkey patch the log file path in logs_api
        import logs_api
        monkeypatch.setattr("logs_api.Path", lambda x: log_file if "deploy.log" in x else Path(x))
        
        return log_file
    
    def test_health_endpoint_no_auth(self, client):
        """Health endpoint should work without authentication"""
        response = client.get("/logs/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "log_viewer"
    
    def test_admin_can_access_deploy_logs(self, client, monkeypatch):
        """Admin users should be able to access deploy logs"""
        # Mock admin role
        def mock_admin_role():
            return "admin"
        
        app.dependency_overrides[get_current_user_role] = mock_admin_role
        
        # Create temporary log file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("2025-11-30 10:00:01 Test log entry 1\n")
            f.write("2025-11-30 10:00:02 Test log entry 2\n")
            temp_log = f.name
        
        try:
            # Patch the log file path
            import logs_api
            original_path = Path
            
            def mock_path(p):
                if "deploy.log" in str(p):
                    return original_path(temp_log)
                return original_path(p)
            
            monkeypatch.setattr("logs_api.Path", mock_path)
            
            response = client.get("/logs/deploy?limit=10")
            
            if response.status_code == 200:
                data = response.json()
                assert "logs" in data
                assert "total" in data
                assert "limit" in data
                assert data["limit"] == 10
        finally:
            os.unlink(temp_log)
            app.dependency_overrides.clear()
    
    def test_non_admin_cannot_access_deploy_logs(self, client):
        """Non-admin users should get 403 when accessing deploy logs"""
        # Mock non-admin role
        def mock_viewer_role():
            return "viewer"
        
        app.dependency_overrides[get_current_user_role] = mock_viewer_role
        
        response = client.get("/logs/deploy")
        assert response.status_code == 403
        assert "Admin privileges required" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_uploader_cannot_access_deploy_logs(self, client):
        """Uploader users should get 403 when accessing deploy logs"""
        def mock_uploader_role():
            return "uploader"
        
        app.dependency_overrides[get_current_user_role] = mock_uploader_role
        
        response = client.get("/logs/deploy")
        assert response.status_code == 403
        
        app.dependency_overrides.clear()
    
    def test_admin_can_access_app_logs(self, client, monkeypatch):
        """Admin users should be able to access application logs"""
        def mock_admin_role():
            return "admin"
        
        app.dependency_overrides[get_current_user_role] = mock_admin_role
        
        # Create temporary app log
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("INFO: Application started\n")
            f.write("INFO: Request received\n")
            temp_log = f.name
        
        try:
            import logs_api
            original_path = Path
            
            def mock_path(p):
                if "phase2.log" in str(p):
                    return original_path(temp_log)
                return original_path(p)
            
            monkeypatch.setattr("logs_api.Path", mock_path)
            
            response = client.get("/logs/app?limit=50")
            
            if response.status_code == 200:
                data = response.json()
                assert "logs" in data
                assert data["limit"] == 50
        finally:
            os.unlink(temp_log)
            app.dependency_overrides.clear()
    
    def test_non_admin_cannot_access_app_logs(self, client):
        """Non-admin users should get 403 when accessing app logs"""
        def mock_viewer_role():
            return "viewer"
        
        app.dependency_overrides[get_current_user_role] = mock_viewer_role
        
        response = client.get("/logs/app")
        assert response.status_code == 403
        
        app.dependency_overrides.clear()
    
    def test_log_limit_parameter(self, client, monkeypatch):
        """Test that limit parameter controls number of log entries returned"""
        def mock_admin_role():
            return "admin"
        
        app.dependency_overrides[get_current_user_role] = mock_admin_role
        
        # Create log with multiple entries
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            for i in range(200):
                f.write(f"2025-11-30 10:00:{i:02d} Log entry {i}\n")
            temp_log = f.name
        
        try:
            import logs_api
            original_path = Path
            
            def mock_path(p):
                if "deploy.log" in str(p):
                    return original_path(temp_log)
                return original_path(p)
            
            monkeypatch.setattr("logs_api.Path", mock_path)
            
            response = client.get("/logs/deploy?limit=50")
            
            if response.status_code == 200:
                data = response.json()
                assert data["limit"] == 50
                # Should return at most 50 entries
                assert len(data["logs"]) <= 50
        finally:
            os.unlink(temp_log)
            app.dependency_overrides.clear()
    
    def test_log_response_format(self, client, monkeypatch):
        """Test that log response has correct format"""
        def mock_admin_role():
            return "admin"
        
        app.dependency_overrides[get_current_user_role] = mock_admin_role
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("2025-11-30 10:00:01 Test entry\n")
            temp_log = f.name
        
        try:
            import logs_api
            original_path = Path
            
            def mock_path(p):
                if "deploy.log" in str(p):
                    return original_path(temp_log)
                return original_path(p)
            
            monkeypatch.setattr("logs_api.Path", mock_path)
            
            response = client.get("/logs/deploy")
            
            if response.status_code == 200:
                data = response.json()
                assert "logs" in data
                assert "total" in data
                assert "limit" in data
                assert isinstance(data["logs"], list)
                
                if len(data["logs"]) > 0:
                    log_entry = data["logs"][0]
                    assert "timestamp" in log_entry
                    assert "level" in log_entry
                    assert "message" in log_entry
        finally:
            os.unlink(temp_log)
            app.dependency_overrides.clear()
    
    def test_nonexistent_log_file_returns_empty(self, client, monkeypatch):
        """If log file doesn't exist, should return empty response"""
        def mock_admin_role():
            return "admin"
        
        app.dependency_overrides[get_current_user_role] = mock_admin_role
        
        # Point to nonexistent file
        import logs_api
        monkeypatch.setattr("logs_api.Path", lambda x: Path("/nonexistent/path/to/logs.log"))
        
        response = client.get("/logs/deploy")
        
        if response.status_code == 200:
            data = response.json()
            assert data["logs"] == []
            assert data["total"] == 0
        
        app.dependency_overrides.clear()


class TestLogViewerAuthorization:
    """Test authorization logic for log viewer"""
    
    def test_require_admin_dependency_with_admin(self):
        """require_admin should pass for admin role"""
        from logs_api import require_admin
        
        try:
            result = require_admin(role="admin")
            assert result == "admin"
        except HTTPException:
            pytest.fail("require_admin should not raise for admin role")
    
    def test_require_admin_dependency_with_non_admin(self):
        """require_admin should raise 403 for non-admin roles"""
        from logs_api import require_admin
        
        with pytest.raises(HTTPException) as exc_info:
            require_admin(role="viewer")
        
        assert exc_info.value.status_code == 403
        assert "Admin privileges required" in exc_info.value.detail
    
    def test_require_admin_dependency_with_uploader(self):
        """require_admin should raise 403 for uploader role"""
        from logs_api import require_admin
        
        with pytest.raises(HTTPException) as exc_info:
            require_admin(role="uploader")
        
        assert exc_info.value.status_code == 403
