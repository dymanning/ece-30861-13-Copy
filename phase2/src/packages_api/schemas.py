from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


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

    class Config:
        orm_mode = True
