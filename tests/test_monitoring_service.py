"""
Unit tests for monitoring service
Tests the core monitoring.py module functions
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add phase2/src to path
PHASE2_SRC = Path(__file__).parent.parent / "phase2" / "src"
sys.path.insert(0, str(PHASE2_SRC))

from packages_api.monitoring import (
    MonitoringResult,
    run_security_check,
    check_artifact_sensitivity,
    save_monitoring_result,
)


class TestMonitoringResult:
    """Test MonitoringResult class"""
    
    def test_init_basic(self):
        """Test basic initialization"""
        result = MonitoringResult(
            exit_code=0,
            stdout="test output",
            stderr="",
            duration_ms=100
        )
        
        assert result.exit_code == 0
        assert result.stdout == "test output"
        assert result.stderr == ""
        assert result.duration_ms == 100
        assert result.timed_out is False
        assert result.error is None
    
    def test_init_with_error(self):
        """Test initialization with error"""
        result = MonitoringResult(
            exit_code=255,
            stdout="",
            stderr="Script failed",
            duration_ms=50,
            error="Node.js not found"
        )
        
        assert result.exit_code == 255
        assert result.error == "Node.js not found"
    
    def test_is_allowed_exit_0(self):
        """Test exit code 0 is allowed"""
        result = MonitoringResult(0, "", "", 100)
        assert result.is_allowed() is True
    
    def test_is_allowed_exit_1(self):
        """Test exit code 1 (warning) is allowed"""
        result = MonitoringResult(1, "", "", 100)
        assert result.is_allowed() is True
    
    def test_is_allowed_exit_2_blocked(self):
        """Test exit code 2 is blocked"""
        result = MonitoringResult(2, "", "", 100)
        assert result.is_allowed() is False
    
    def test_is_allowed_exit_high_blocked(self):
        """Test high exit codes are blocked"""
        result = MonitoringResult(255, "", "", 100)
        assert result.is_allowed() is False
    
    def test_is_allowed_timeout_blocked(self):
        """Test timeout is blocked"""
        result = MonitoringResult(124, "", "", 5000, timed_out=True)
        assert result.is_allowed() is False
    
    def test_is_allowed_error_blocked(self):
        """Test errors are blocked"""
        result = MonitoringResult(127, "", "", 0, error="Script not found")
        assert result.is_allowed() is False
    
    def test_get_action_allowed(self):
        """Test get_action for allowed"""
        result = MonitoringResult(0, "", "", 100)
        assert result.get_action() == "allowed"
    
    def test_get_action_warned(self):
        """Test get_action for warning"""
        result = MonitoringResult(1, "", "", 100)
        assert result.get_action() == "warned"
    
    def test_get_action_blocked(self):
        """Test get_action for blocked"""
        result = MonitoringResult(2, "", "", 100)
        assert result.get_action() == "blocked"
    
    def test_get_action_timeout(self):
        """Test get_action for timeout"""
        result = MonitoringResult(124, "", "", 5000, timed_out=True)
        assert result.get_action() == "error"  # Timeouts return 'error'
    
    def test_get_action_error(self):
        """Test get_action for error"""
        result = MonitoringResult(127, "", "", 0, error="Script not found")
        assert result.get_action() == "error"
    
    def test_to_dict(self):
        """Test serialization to dict"""
        result = MonitoringResult(
            exit_code=0,
            stdout='{"test": "data"}',
            stderr="",
            duration_ms=150
        )
        
        data = result.to_dict()
        
        assert data["exit_code"] == 0
        assert data["stdout"] == '{"test": "data"}'
        assert data["duration_ms"] == 150
        assert data["action"] == "allowed"
        assert data["allowed"] is True
    
    def test_output_truncation(self):
        """Test output is truncated to 10KB"""
        long_output = "x" * 20000  # 20KB
        result = MonitoringResult(0, long_output, "", 100)
        
        assert len(result.stdout) == 10000
        assert result.stdout == "x" * 10000


class TestRunSecurityCheck:
    """Test run_security_check function"""
    
    @patch('packages_api.monitoring.subprocess.run')
    def test_run_security_check_success(self, mock_run):
        """Test successful security check"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"recommendation": "allow"}',
            stderr=""
        )
        
        result = run_security_check(
            artifact_id="123",
            artifact_name="safe-model",
            script_name="default-check.js"
        )
        
        assert result.exit_code == 0
        assert "allow" in result.stdout
        assert result.is_allowed() is True
        mock_run.assert_called_once()
    
    @patch('packages_api.monitoring.subprocess.run')
    def test_run_security_check_blocked(self, mock_run):
        """Test blocked artifact"""
        mock_run.return_value = Mock(
            returncode=2,
            stdout='{"recommendation": "block", "findings": ["malware detected"]}',
            stderr=""
        )
        
        result = run_security_check(
            artifact_id="456",
            artifact_name="malware-backdoor",
            script_name="default-check.js"
        )
        
        assert result.exit_code == 2
        assert "block" in result.stdout
        assert result.is_allowed() is False
    
    @patch('packages_api.monitoring.subprocess.run')
    def test_run_security_check_warning(self, mock_run):
        """Test warning (exit 1)"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='{"recommendation": "warn", "findings": ["long name"]}',
            stderr=""
        )
        
        result = run_security_check(
            artifact_id="789",
            artifact_name="very-long-artifact-name" * 20,
            script_name="default-check.js"
        )
        
        assert result.exit_code == 1
        assert result.is_allowed() is True  # Warnings still allow
        assert result.get_action() == "warned"
    
    @patch('packages_api.monitoring.subprocess.run')
    def test_run_security_check_timeout(self, mock_run):
        """Test script timeout"""
        from subprocess import TimeoutExpired
        
        mock_run.side_effect = TimeoutExpired(
            cmd=["node", "script.js"],
            timeout=5
        )
        
        result = run_security_check(
            artifact_id="999",
            artifact_name="slow-check",
            script_name="default-check.js"
        )
        
        assert result.timed_out is True
        assert result.is_allowed() is False
        assert result.get_action() == "error"  # Timeouts return 'error'
    
    @patch('packages_api.monitoring.subprocess.run')
    def test_run_security_check_script_not_found(self, mock_run):
        """Test missing script file"""
        mock_run.side_effect = FileNotFoundError("Script not found")
        
        result = run_security_check(
            artifact_id="111",
            artifact_name="test",
            script_name="missing-script.js"
        )
        
        assert result.error is not None
        assert result.is_allowed() is False
        assert "not found" in result.error.lower()
    
    @patch('packages_api.monitoring.subprocess.run')
    def test_run_security_check_node_not_found(self, mock_run):
        """Test Node.js not installed"""
        mock_run.side_effect = FileNotFoundError("node not found")
        
        result = run_security_check(
            artifact_id="222",
            artifact_name="test",
            script_name="default-check.js"
        )
        
        assert result.error is not None
        assert result.is_allowed() is False
    
    @patch('packages_api.monitoring.subprocess.run')
    def test_run_security_check_with_artifact_type(self, mock_run):
        """Test passing artifact type to script"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"recommendation": "allow"}',
            stderr=""
        )
        
        result = run_security_check(
            artifact_id="333",
            artifact_name="model",
            artifact_type="model",
            script_name="default-check.js"
        )
        
        # Check that type was passed as argument
        call_args = mock_run.call_args[0][0]
        assert "--type" in call_args
        assert "model" in call_args


class TestCheckArtifactSensitivity:
    """Test check_artifact_sensitivity function"""
    
    def test_check_artifact_sensitivity_packages_table(self):
        """Test checking sensitivity from packages table"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (True, "default-check.js")
        mock_db.execute.return_value = mock_result
        
        is_sensitive, script = check_artifact_sensitivity(mock_db, "123")
        
        assert is_sensitive is True
        assert script == "default-check.js"
    
    def test_check_artifact_sensitivity_not_sensitive(self):
        """Test non-sensitive artifact"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (False, None)
        mock_db.execute.return_value = mock_result
        
        is_sensitive, script = check_artifact_sensitivity(mock_db, "456")
        
        assert is_sensitive is False
        assert script is None
    
    def test_check_artifact_sensitivity_not_found(self):
        """Test artifact not found"""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        
        is_sensitive, script = check_artifact_sensitivity(mock_db, "999")
        
        assert is_sensitive is False
        assert script is None
    
    def test_check_artifact_sensitivity_fallback_to_artifacts(self):
        """Test fallback to artifacts table when ID is not integer"""
        mock_db = Mock()
        
        # Setup two different results
        # First call (packages) returns None
        mock_result_packages = Mock()
        mock_result_packages.fetchone.return_value = None
        
        # Second call (artifacts) returns success
        mock_result_artifacts = Mock()
        mock_result_artifacts.fetchone.return_value = (True, "size-limit-check.js")
        
        # db.execute will be called twice with side_effect to return different results
        mock_db.execute.side_effect = [mock_result_packages, mock_result_artifacts]
        
        # Use integer ID but ensure packages table returns None to force artifacts fallback
        is_sensitive, script = check_artifact_sensitivity(mock_db, "123")
        
        # Should fallback to artifacts table and succeed
        assert is_sensitive is True
        assert script == "size-limit-check.js"
        # Execute should be called twice (packages attempt + artifacts fallback)
        assert mock_db.execute.call_count == 2


class TestSaveMonitoringResult:
    """Test save_monitoring_result function"""
    
    def test_save_monitoring_result(self):
        """Test saving monitoring result to database"""
        mock_db = Mock()
        mock_result_proxy = Mock()
        mock_result_proxy.fetchone.return_value = (42,)  # Inserted ID
        mock_db.execute.return_value = mock_result_proxy
        
        result = MonitoringResult(
            exit_code=0,
            stdout='{"test": "data"}',
            stderr="",
            duration_ms=100
        )
        
        inserted_id = save_monitoring_result(
            db=mock_db,
            artifact_id="123",
            result=result,
            script_name="default-check.js",
            user_id="user-456",
            user_is_admin=False,
            metadata={"source": "test"}
        )
        
        assert inserted_id == 42
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_save_monitoring_result_no_user(self):
        """Test saving without user info"""
        mock_db = Mock()
        mock_result_proxy = Mock()
        mock_result_proxy.fetchone.return_value = (99,)
        mock_db.execute.return_value = mock_result_proxy
        
        result = MonitoringResult(2, "blocked", "", 50)
        
        inserted_id = save_monitoring_result(
            db=mock_db,
            artifact_id="789",
            result=result,
            script_name="default-check.js"
        )
        
        assert inserted_id == 99
