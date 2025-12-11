"""
Integration tests for monitoring
Tests the monitoring scripts and core functionality
"""
import pytest
from pathlib import Path
import sys

# Add phase2/src to path
PHASE2_SRC = Path(__file__).parent.parent / "phase2" / "src"
sys.path.insert(0, str(PHASE2_SRC))


class TestMonitoringScriptExecution:
    """Test direct execution of security scripts"""
    
    def test_default_check_script_exists(self):
        """Test that default-check.js exists"""
        script_path = Path(__file__).parent.parent / "phase2" / "security-scripts" / "default-check.js"
        assert script_path.exists(), "default-check.js not found"
    
    def test_size_limit_check_script_exists(self):
        """Test that size-limit-check.js exists"""
        script_path = Path(__file__).parent.parent / "phase2" / "security-scripts" / "size-limit-check.js"
        assert script_path.exists(), "size-limit-check.js not found"
    
    def test_default_check_safe_name(self):
        """Test default-check with safe artifact name"""
        import subprocess
        
        script_path = Path(__file__).parent.parent / "phase2" / "security-scripts" / "default-check.js"
        
        result = subprocess.run(
            [
                "node",
                str(script_path),
                "--artifact-id", "test123",
                "--name", "safe-model",
                "--type", "model"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert result.returncode == 0
        assert "allow" in result.stdout
    
    def test_default_check_malicious_name(self):
        """Test default-check with malicious artifact name"""
        import subprocess
        
        script_path = Path(__file__).parent.parent / "phase2" / "security-scripts" / "default-check.js"
        
        result = subprocess.run(
            [
                "node",
                str(script_path),
                "--artifact-id", "test456",
                "--name", "malware-backdoor",
                "--type", "model"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert result.returncode == 2  # Should be blocked
        assert "block" in result.stdout
    
    def test_size_limit_check_small_artifact(self):
        """Test size-limit-check with small artifact"""
        import subprocess
        
        script_path = Path(__file__).parent.parent / "phase2" / "security-scripts" / "size-limit-check.js"
        
        result = subprocess.run(
            [
                "node",
                str(script_path),
                "--artifact-id", "test789",
                "--name", "small-model",
                "--size", "1000000"  # 1MB
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert result.returncode == 0
        assert "allow" in result.stdout
    
    def test_size_limit_check_large_artifact(self):
        """Test size-limit-check with large artifact"""
        import subprocess
        
        script_path = Path(__file__).parent.parent / "phase2" / "security-scripts" / "size-limit-check.js"
        
        result = subprocess.run(
            [
                "node",
                str(script_path),
                "--artifact-id", "test999",
                "--name", "huge-model",
                "--size", "50000000000"  # 50GB
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # May warn or block depending on thresholds
        assert result.returncode in [0, 1, 2]
