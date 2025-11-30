"""
Sensitive Model Monitoring Service
Executes Node.js security scripts before artifact downloads
"""

import subprocess
import time
import json
import os
from typing import Dict, Optional, Tuple
from pathlib import Path

# Security script configuration
SECURITY_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "security-scripts"
DEFAULT_SCRIPT = "default-check.js"
SCRIPT_TIMEOUT_SECONDS = 5
MAX_OUTPUT_LENGTH = 10000


class MonitoringResult:
    """Container for monitoring execution results"""
    
    def __init__(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: int,
        timed_out: bool = False,
        error: Optional[str] = None
    ):
        self.exit_code = exit_code
        self.stdout = stdout[:MAX_OUTPUT_LENGTH] if stdout else ""
        self.stderr = stderr[:MAX_OUTPUT_LENGTH] if stderr else ""
        self.duration_ms = duration_ms
        self.timed_out = timed_out
        self.error = error
    
    def is_allowed(self) -> bool:
        """Determine if download should be allowed based on exit code"""
        # Exit code 0 = safe, 1 = warning (allow), 2+ = block
        return self.exit_code in [0, 1]
    
    def get_action(self) -> str:
        """Get action taken based on exit code"""
        if self.error or self.timed_out:
            return "error"
        elif self.exit_code == 0:
            return "allowed"
        elif self.exit_code == 1:
            return "warned"
        else:
            return "blocked"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "error": self.error,
            "action": self.get_action(),
            "allowed": self.is_allowed()
        }


def run_security_check(
    artifact_id: str,
    artifact_name: str,
    artifact_type: Optional[str] = None,
    script_name: str = DEFAULT_SCRIPT
) -> MonitoringResult:
    """
    Execute Node.js security script for artifact
    
    Args:
        artifact_id: Unique artifact identifier
        artifact_name: Human-readable artifact name
        artifact_type: Type of artifact (model, dataset, code)
        script_name: Name of script to execute
    
    Returns:
        MonitoringResult with execution details
    """
    script_path = SECURITY_SCRIPTS_DIR / script_name
    
    # Validate script exists
    if not script_path.exists():
        return MonitoringResult(
            exit_code=255,
            stdout="",
            stderr=f"Security script not found: {script_name}",
            duration_ms=0,
            error=f"Script not found: {script_path}"
        )
    
    # Build command
    cmd = [
        "node",
        str(script_path),
        "--artifact-id", str(artifact_id),
        "--name", artifact_name
    ]
    
    if artifact_type:
        cmd.extend(["--type", artifact_type])
    
    # Execute script
    start_time = time.time()
    timed_out = False
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT_SECONDS,
            cwd=str(SECURITY_SCRIPTS_DIR)
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return MonitoringResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
            timed_out=False
        )
        
    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.time() - start_time) * 1000)
        timed_out = True
        
        return MonitoringResult(
            exit_code=124,  # Standard timeout exit code
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "Script execution timed out",
            duration_ms=duration_ms,
            timed_out=True,
            error=f"Script timed out after {SCRIPT_TIMEOUT_SECONDS} seconds"
        )
        
    except FileNotFoundError:
        return MonitoringResult(
            exit_code=127,
            stdout="",
            stderr="Node.js not found in PATH",
            duration_ms=0,
            error="Node.js executable not found"
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        return MonitoringResult(
            exit_code=255,
            stdout="",
            stderr=str(e),
            duration_ms=duration_ms,
            error=f"Unexpected error: {str(e)}"
        )


def save_monitoring_result(
    db,
    artifact_id: str,
    result: MonitoringResult,
    script_name: str,
    user_id: Optional[str] = None,
    user_is_admin: bool = False,
    metadata: Optional[Dict] = None
) -> int:
    """
    Save monitoring result to database
    
    Args:
        db: Database session
        artifact_id: Artifact identifier
        result: MonitoringResult object
        script_name: Name of executed script
        user_id: Optional user identifier
        user_is_admin: Whether user is admin
        metadata: Optional additional metadata
    
    Returns:
        ID of created monitoring_history record
    """
    from sqlalchemy import text
    
    query = text("""
        INSERT INTO monitoring_history (
            artifact_id,
            script_name,
            execution_duration_ms,
            user_id,
            user_is_admin,
            exit_code,
            stdout,
            stderr,
            action_taken,
            metadata
        ) VALUES (
            :artifact_id,
            :script_name,
            :duration_ms,
            :user_id,
            :user_is_admin,
            :exit_code,
            :stdout,
            :stderr,
            :action_taken,
            :metadata::jsonb
        )
        RETURNING id
    """)
    
    params = {
        "artifact_id": artifact_id,
        "script_name": script_name,
        "duration_ms": result.duration_ms,
        "user_id": user_id,
        "user_is_admin": user_is_admin,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "action_taken": result.get_action(),
        "metadata": json.dumps(metadata or {})
    }
    
    result_proxy = db.execute(query, params)
    db.commit()
    
    row = result_proxy.fetchone()
    return row[0] if row else None


def check_artifact_sensitivity(db, artifact_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if artifact requires monitoring
    
    Args:
        db: Database session
        artifact_id: Package/artifact identifier (integer or string)
    
    Returns:
        Tuple of (is_sensitive, monitoring_script_name)
    """
    from sqlalchemy import text
    
    # Try packages table first (used by main API)
    query = text("""
        SELECT is_sensitive, monitoring_script
        FROM packages
        WHERE id = :artifact_id
    """)
    
    try:
        result = db.execute(query, {"artifact_id": int(artifact_id)}).fetchone()
        if result:
            return result[0], result[1] if result[0] else None
    except (ValueError, Exception):
        pass
    
    # Fallback to artifacts table (for future use)
    query = text("""
        SELECT is_sensitive, monitoring_script
        FROM artifacts
        WHERE id = :artifact_id
    """)
    
    result = db.execute(query, {"artifact_id": artifact_id}).fetchone()
    
    if not result:
        return False, None
    
    return result[0], result[1] if result[0] else None
