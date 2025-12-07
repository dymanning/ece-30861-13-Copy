from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .database import get_db
from .audit import query_audit_logs
from .schemas import AuditLogOut
from .. import logs_api

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=List[AuditLogOut])
def export_audit_logs(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: str = Depends(logs_api.require_admin),
):
    return query_audit_logs(db, start=start, end=end, user_id=user_id, action=action, limit=limit)
