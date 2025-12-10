from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from .models import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    resource_type: Optional[str] = None,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Insert a single audit record. Non-blocking (logs error and continues)."""
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
    except Exception as exc:  # pragma: no cover - defensive path
        db.rollback()
        print(f"Warning: failed to record audit log: {exc}")


def query_audit_logs(
    db: Session,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 1000,
) -> List[AuditLog]:
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
    return q.limit(limit).all()
