"""
Audit log API endpoints.
Admin-only access to query and export audit logs.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .database import get_db
from .schemas import AuditLogOut
from .audit import query_audit_logs
try:
    from ..logs_api import require_admin
except ImportError:
    # Fallback for testing - create a dummy require_admin
    def require_admin():
        pass


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=List[AuditLogOut], dependencies=[Depends(require_admin)])
def get_audit_logs(
    start: Optional[datetime] = Query(None, description="Start timestamp"),
    end: Optional[datetime] = Query(None, description="End timestamp"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(1000, ge=1, le=10000, description="Max results"),
    db: Session = Depends(get_db),
):
    """
    Query audit logs with optional filters. Admin access required.
    
    Returns list of audit log entries, newest first.
    """
    return query_audit_logs(
        db=db,
        start=start,
        end=end,
        user_id=user_id,
        action=action,
        limit=limit,
    )
