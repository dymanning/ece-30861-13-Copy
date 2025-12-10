from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PackageCreate(BaseModel):
    name: str
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PackageUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PackageOut(BaseModel):
    id: int
    name: str
    version: Optional[str] = None
    s3_uri: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogOut(BaseModel):
    id: int
    action: str
    user_id: Optional[str] = None
    resource: Optional[str] = None
    resource_type: Optional[str] = None
    success: bool
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
