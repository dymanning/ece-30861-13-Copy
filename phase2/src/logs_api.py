"""
Log Viewer API Endpoint
Admin-only endpoint to view recent deployment and application logs
"""
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel


router = APIRouter(prefix="/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Single log entry"""
    timestamp: str
    level: str
    message: str


class LogResponse(BaseModel):
    """Log viewer response"""
    logs: List[LogEntry]
    total: int
    limit: int


def get_current_user_role() -> str:
    """
    Mock function to get current user's role from auth token
    In production, this would verify JWT and extract role
    """
    return "admin"


def require_admin(role: str = Depends(get_current_user_role)):
    """Dependency to ensure only admin users can access"""
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return role


@router.get("/deploy", response_model=LogResponse)
async def get_deploy_logs(
    limit: int = Query(100, ge=1, le=1000),
    role: str = Depends(require_admin)
):
    """
    Get recent deployment logs (admin only)
    
    Args:
        limit: Maximum number of log entries to return (1-1000)
        role: User role (injected by dependency, must be admin)
    
    Returns:
        LogResponse with recent deployment log entries
    """
    log_file = Path("/tmp/deploy/deploy.log")
    
    if not log_file.exists():
        return LogResponse(logs=[], total=0, limit=limit)
    
    # Read last N lines from deploy log
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        
        # Take last 'limit' lines
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        # Parse lines into structured log entries
        log_entries = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            
            # Simple parsing - in production would use structured logging
            parts = line.split(" ", 2)
            if len(parts) >= 3:
                timestamp = parts[0] + " " + parts[1]
                level = "INFO"  # Default level
                message = parts[2]
            else:
                timestamp = ""
                level = "INFO"
                message = line
            
            log_entries.append(LogEntry(
                timestamp=timestamp,
                level=level,
                message=message
            ))
        
        return LogResponse(
            logs=log_entries,
            total=len(log_entries),
            limit=limit
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading deploy logs: {str(e)}"
        )


@router.get("/app", response_model=LogResponse)
async def get_app_logs(
    limit: int = Query(100, ge=1, le=1000),
    role: str = Depends(require_admin)
):
    """
    Get recent application logs (admin only)
    
    Args:
        limit: Maximum number of log entries to return (1-1000)
        role: User role (injected by dependency, must be admin)
    
    Returns:
        LogResponse with recent application log entries
    """
    log_file = Path("/var/log/phase2.log")
    
    if not log_file.exists():
        return LogResponse(logs=[], total=0, limit=limit)
    
    # Read last N lines from app log
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        log_entries = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse log line (assuming basic format)
            log_entries.append(LogEntry(
                timestamp="",
                level="INFO",
                message=line
            ))
        
        return LogResponse(
            logs=log_entries,
            total=len(log_entries),
            limit=limit
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading app logs: {str(e)}"
        )


@router.get("/health")
async def logs_health():
    """Health check for logs endpoint (no auth required)"""
    return {"status": "ok", "service": "log_viewer"}
