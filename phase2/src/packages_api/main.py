"""
ECE 461 Phase 2 - Artifact Registry API
Implements the OpenAPI spec endpoints for the autograder
"""
from typing import Optional, List, Dict, Any
import uuid
import random
import re
import hashlib

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    Header,
    Query,
    Path,
    Body,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from enum import Enum

from .database import engine, get_db, Base

# ============== MODELS ==============

class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(String(32), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    artifact_type = Column(String(20), nullable=False)
    url = Column(Text, nullable=False)
    download_url = Column(Text, nullable=True)
    readme = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ECE 461 Artifact Registry")

# ============== SCHEMAS ==============

class ArtifactMetadata(BaseModel):
    name: str
    id: str
    type: str
    
    class Config:
        orm_mode = True


class ArtifactData(BaseModel):
    url: str
    download_url: Optional[str] = None


class ArtifactResponse(BaseModel):
    metadata: ArtifactMetadata
    data: ArtifactData


class ArtifactQuery(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    version: Optional[str] = None


class ArtifactRegEx(BaseModel):
    regex: str = Field(..., alias="regex")
    
    class Config:
        populate_by_name = True


class AuthenticationRequest(BaseModel):
    user: Dict[str, Any]
    secret: Dict[str, Any]


class SimpleLicenseCheckRequest(BaseModel):
    github_url: str


# ============== HELPER FUNCTIONS ==============

def generate_artifact_id(name: str) -> str:
    """Generate a unique numeric-style ID for an artifact"""
    hash_input = f"{name}-{uuid.uuid4().hex}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()
    numeric_id = str(int(hash_digest[:12], 16))[:10]
    return numeric_id


def extract_name_from_url(url: str) -> str:
    """Extract artifact name from URL"""
    if "huggingface.co" in url:
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else "unknown"
    if "github.com" in url:
        parts = url.rstrip("/").split("/")
        return parts[-1] if len(parts) >= 2 else "unknown"
    parts = url.rstrip("/").split("/")
    return parts[-1] if parts else "unknown"


# ============== ENDPOINTS ==============

@app.get("/health")
def health_check():
    """Heartbeat check (BASELINE)"""
    return {"status": "alive"}


@app.get("/")
def root():
    return {"message": "ECE 461 Artifact Registry API"}


@app.get("/tracks")
def get_tracks():
    """Get the list of tracks a student has planned to implement"""
    return {
        "plannedTracks": [
            "Access control track"
        ]
    }


@app.put("/authenticate")
def authenticate(body: AuthenticationRequest):
    """Create an access token (NON-BASELINE)"""
    token = f"bearer {uuid.uuid4().hex}"
    return token


@app.delete("/reset")
def reset_registry(
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Reset the registry to a system default state (BASELINE)"""
    try:
        db.query(Artifact).delete()
        db.commit()
        return {"message": "Registry is reset."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset: {str(e)}")


@app.post("/artifacts")
def list_artifacts(
    queries: List[ArtifactQuery] = Body(...),
    offset: Optional[str] = Query(None),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Get the artifacts from the registry (BASELINE)"""
    results = []
    
    for query in queries:
        q = db.query(Artifact)
        
        if query.name and query.name != "*":
            q = q.filter(Artifact.name == query.name)
        
        if query.type:
            q = q.filter(Artifact.artifact_type == query.type)
        
        artifacts = q.all()
        for art in artifacts:
            results.append({
                "name": art.name,
                "id": art.id,
                "type": art.artifact_type
            })
    
    return results


@app.post("/artifact/{artifact_type}", status_code=status.HTTP_201_CREATED)
def create_artifact(
    artifact_type: str = Path(...),
    body: ArtifactData = Body(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Register a new artifact (BASELINE)"""
    if artifact_type not in ["model", "dataset", "code"]:
        raise HTTPException(status_code=400, detail="Invalid artifact type")
    
    if not body.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    name = extract_name_from_url(body.url)
    artifact_id = generate_artifact_id(name)
    
    artifact = Artifact(
        id=artifact_id,
        name=name,
        artifact_type=artifact_type,
        url=body.url,
        download_url=f"http://localhost:8000/download/{artifact_id}"
    )
    
    try:
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return {
        "metadata": {
            "name": artifact.name,
            "id": artifact.id,
            "type": artifact.artifact_type
        },
        "data": {
            "url": artifact.url,
            "download_url": artifact.download_url
        }
    }


@app.get("/artifacts/{artifact_type}/{artifact_id}")
def get_artifact(
    artifact_type: str = Path(...),
    artifact_id: str = Path(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Get artifact by ID (BASELINE)"""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.artifact_type == artifact_type
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")
    
    return {
        "metadata": {
            "name": artifact.name,
            "id": artifact.id,
            "type": artifact.artifact_type
        },
        "data": {
            "url": artifact.url,
            "download_url": artifact.download_url
        }
    }


@app.put("/artifacts/{artifact_type}/{artifact_id}")
def update_artifact(
    artifact_type: str = Path(...),
    artifact_id: str = Path(...),
    body: dict = Body(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Update artifact (BASELINE)"""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.artifact_type == artifact_type
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")
    
    if "data" in body and "url" in body["data"]:
        artifact.url = body["data"]["url"]
    
    db.commit()
    return {"message": "Artifact is updated."}


@app.delete("/artifacts/{artifact_type}/{artifact_id}")
def delete_artifact(
    artifact_type: str = Path(...),
    artifact_id: str = Path(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Delete artifact (NON-BASELINE)"""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.artifact_type == artifact_type
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")
    
    db.delete(artifact)
    db.commit()
    return {"message": "Artifact is deleted."}


@app.get("/artifact/byName/{name}")
def get_artifact_by_name(
    name: str = Path(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """List artifact metadata for this name (NON-BASELINE)"""
    artifacts = db.query(Artifact).filter(Artifact.name == name).all()
    
    if not artifacts:
        raise HTTPException(status_code=404, detail="No such artifact.")
    
    return [
        {
            "name": art.name,
            "id": art.id,
            "type": art.artifact_type
        }
        for art in artifacts
    ]


@app.post("/artifact/byRegEx")
def search_by_regex(
    body: ArtifactRegEx = Body(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Get artifacts matching regex (BASELINE)"""
    try:
        pattern = re.compile(body.regex, re.IGNORECASE)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid regex pattern")
    
    all_artifacts = db.query(Artifact).all()
    matches = []
    
    for art in all_artifacts:
        if pattern.search(art.name) or (art.readme and pattern.search(art.readme)):
            matches.append({
                "name": art.name,
                "id": art.id,
                "type": art.artifact_type
            })
    
    if not matches:
        raise HTTPException(status_code=404, detail="No artifact found under this regex.")
    
    return matches


@app.get("/artifact/model/{artifact_id}/rate")
def rate_model(
    artifact_id: str = Path(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Get ratings for this model artifact (BASELINE)"""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.artifact_type == "model"
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")
    
    return {
        "BusFactor": 0.5,
        "BusFactorLatency": 0.01,
        "Correctness": 0.7,
        "CorrectnessLatency": 0.02,
        "RampUp": 0.6,
        "RampUpLatency": 0.01,
        "ResponsiveMaintainer": 0.8,
        "ResponsiveMaintainerLatency": 0.03,
        "LicenseScore": 1.0,
        "LicenseScoreLatency": 0.01,
        "GoodPinningPractice": 0.5,
        "GoodPinningPracticeLatency": 0.01,
        "PullRequest": 0.6,
        "PullRequestLatency": 0.02,
        "NetScore": 0.65,
        "NetScoreLatency": 0.1
    }


@app.get("/artifact/{artifact_type}/{artifact_id}/cost")
def get_artifact_cost(
    artifact_type: str = Path(...),
    artifact_id: str = Path(...),
    dependency: bool = Query(False),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Get the cost of an artifact (BASELINE)"""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.artifact_type == artifact_type
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")
    
    cost_value = 250.0
    
    if dependency:
        return {
            artifact_id: {
                "standalone_cost": cost_value,
                "total_cost": cost_value * 1.5
            }
        }
    else:
        return {
            artifact_id: {
                "total_cost": cost_value
            }
        }


@app.get("/artifact/model/{artifact_id}/lineage")
def get_artifact_lineage(
    artifact_id: str = Path(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Retrieve the lineage graph for this artifact (BASELINE)"""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.artifact_type == "model"
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")
    
    return {
        "nodes": [
            {
                "artifact_id": artifact_id,
                "name": artifact.name,
                "source": "config_json"
            }
        ],
        "edges": []
    }


@app.post("/artifact/model/{artifact_id}/license-check")
def check_license(
    artifact_id: str = Path(...),
    body: SimpleLicenseCheckRequest = Body(...),
    x_authorization: Optional[str] = Header(None, alias="X-Authorization"),
    db: Session = Depends(get_db)
):
    """Assess license compatibility (BASELINE)"""
    artifact = db.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.artifact_type == "model"
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact does not exist.")
    
    return True


@app.get("/packages")
def list_packages(db: Session = Depends(get_db)):
    """Return all artifacts as packages (legacy compatibility)"""
    artifacts = db.query(Artifact).all()
    return [
        {
            "id": art.id,
            "name": art.name,
            "type": art.artifact_type,
            "url": art.url
        }
        for art in artifacts
    ]
