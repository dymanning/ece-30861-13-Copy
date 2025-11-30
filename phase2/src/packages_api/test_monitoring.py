"""
Test script for monitoring functionality
Run with: python -m pytest test_monitoring.py -v
"""

import pytest
from monitoring import run_security_check, MonitoringResult


def test_safe_artifact():
    """Test that safe artifact passes check"""
    result = run_security_check(
        artifact_id="test123",
        artifact_name="safe-model",
        artifact_type="model"
    )
    
    assert result.exit_code in [0, 1], "Safe artifact should pass"
    assert result.is_allowed(), "Safe artifact should be allowed"
    assert result.get_action() in ["allowed", "warned"]
    assert result.duration_ms > 0


def test_malicious_artifact():
    """Test that suspicious artifact is blocked"""
    result = run_security_check(
        artifact_id="test456",
        artifact_name="malware-backdoor",
        artifact_type="model"
    )
    
    assert result.exit_code == 2, "Suspicious artifact should be blocked"
    assert not result.is_allowed(), "Malicious artifact should not be allowed"
    assert result.get_action() == "blocked"
    assert "malware" in result.stdout.lower() or "backdoor" in result.stdout.lower()


def test_missing_script():
    """Test handling of missing script"""
    result = run_security_check(
        artifact_id="test789",
        artifact_name="test-model",
        script_name="nonexistent.js"
    )
    
    assert result.exit_code == 255
    assert result.error is not None
    assert "not found" in result.error.lower()


def test_result_to_dict():
    """Test MonitoringResult serialization"""
    result = MonitoringResult(
        exit_code=0,
        stdout='{"test": "output"}',
        stderr="",
        duration_ms=150
    )
    
    data = result.to_dict()
    assert data["exit_code"] == 0
    assert data["allowed"] is True
    assert data["action"] == "allowed"
    assert data["duration_ms"] == 150


def test_output_truncation():
    """Test that large outputs are truncated"""
    long_output = "x" * 20000  # Longer than MAX_OUTPUT_LENGTH
    
    result = MonitoringResult(
        exit_code=0,
        stdout=long_output,
        stderr="",
        duration_ms=100
    )
    
    assert len(result.stdout) <= 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
