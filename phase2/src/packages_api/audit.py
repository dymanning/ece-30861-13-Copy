"""
Audit logging utilities for tracking user actions.
Simple, non-blocking implementation that won't break existing functionality.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from .database import AuditLog


def record_audit(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    resource_type: Optional[str] = None,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Record an audit log entry. Non-blocking - catches and logs errors internally.
    
    Args:
        db: Database session
        action: Action performed (e.g., 'package.upload', 'package.download')
        user_id: ID of user performing action
        resource: Resource ID (e.g., package ID)
        resource_type: Type of resource (e.g., 'package')
        success: Whether action succeeded
        metadata: Additional context (e.g., version, file size)
    """
    try:
        entry = AuditLog(
            action=action,
            user_id=user_id,
            resource=resource,
            resource_type=resource_type,
            success=success,
            metadata_json=metadata or {},
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        # Don't let audit logging break the main operation
        db.rollback()
        print(f"Warning: Failed to record audit log: {e}")


def query_audit_logs(
    db: Session,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 1000,
) -> List[AuditLog]:
    """
    Query audit logs with optional filters.
    
    Args:
        db: Database session
        start: Filter logs after this timestamp
        end: Filter logs before this timestamp
        user_id: Filter by user ID
        action: Filter by action type
        limit: Maximum results to return (default 1000, max 10000)
    
    Returns:
        List of AuditLog entries, newest first
    """
    q = db.query(AuditLog)
    
    if start:
        q = q.filter(AuditLog.created_at >= start)
    if end:
        q = q.filter(AuditLog.created_at <= end)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    
    q = q.order_by(AuditLog.created_at.desc())
    return q.limit(min(limit, 10000)).all()
