from typing import Optional
import uuid
import json

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import engine, get_db
from . import models
from .schemas import PackageCreate, PackageUpdate, PackageOut
from .crud import create_package, get_package, update_package, delete_package
from .s3_client import S3Client
from .monitoring import (
    run_security_check,
    save_monitoring_result,
    check_artifact_sensitivity
)

# Import log viewer router
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from logs_api import router as logs_router

# Test database connection before creating tables
try:
    with engine.connect() as connection:
        print("✓ Database connection successful")
except Exception as e:
    print(f"✗ Database connection failed: {e}", file=sys.stderr)
    print("Please check your DATABASE_URL environment variable.", file=sys.stderr)
    sys.exit(1)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Packages API")
s3 = S3Client()

# Include log viewer endpoints
app.include_router(logs_router)


@app.get("/health")
def health_check():
    return {"status": "alive"}


@app.get("/")
def root():
    return {"message": "Package Registry API"}


@app.post("/auth/login")
def login(username: str = Form(...), password: str = Form(...)):
    """Simple login stub that always succeeds for demo/testing."""
    token = uuid.uuid4().hex
    return {"access_token": token, "token_type": "bearer", "user": {"username": username}}

@app.get("/health")
def health_check():
    return {"status": "alive"}

@app.get("/")
def root():
    return {"message": "Package Registry API"}


@app.post("/packages", response_model=PackageOut, status_code=status.HTTP_201_CREATED)
async def upload_package(
    name: str = Form(...),
    version: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    meta = None
    if metadata:
        try:
            meta = json.loads(metadata)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    pkg_in = PackageCreate(name=name, version=version, metadata=meta)
    try:
        pkg = create_package(db, pkg_in)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error creating package record")

    key = f"packages/{pkg.id}/{uuid.uuid4().hex}_{file.filename}"
    try:
        s3_uri = s3.upload_fileobj(file.file, key)
        pkg.s3_uri = s3_uri
        db.add(pkg)
        db.commit()
        db.refresh(pkg)
    except Exception:
        try:
            delete_package(db, pkg)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to upload file to S3")

    return pkg


@app.get("/packages")
def list_packages(db: Session = Depends(get_db)):
    """Return all packages (used by reset verification tests)."""
    pkgs = db.query(models.Package).all()
    return [PackageOut.from_orm(p) for p in pkgs]


@app.get("/packages/{pkg_id}")
def download_package(
    pkg_id: int, 
    component: Optional[str] = None, 
    db: Session = Depends(get_db),
    user_id: Optional[str] = None,  # TODO: Extract from auth token
    user_is_admin: bool = False      # TODO: Extract from auth token
):
    pkg = get_package(db, pkg_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    if not pkg.s3_uri:
        raise HTTPException(status_code=404, detail="Package file not available")
    
    # 🔒 SECURITY MONITORING: Check if artifact requires validation
    is_sensitive, script_name = check_artifact_sensitivity(db, str(pkg_id))
    
    if is_sensitive:
        # Execute security check
        monitoring_result = run_security_check(
            artifact_id=str(pkg_id),
            artifact_name=pkg.name,
            artifact_type=None,  # TODO: Add type to package model
            script_name=script_name or "default-check.js"
        )
        
        # Save monitoring result to history
        try:
            save_monitoring_result(
                db=db,
                artifact_id=str(pkg_id),
                result=monitoring_result,
                script_name=script_name or "default-check.js",
                user_id=user_id,
                user_is_admin=user_is_admin,
                metadata={
                    "package_name": pkg.name,
                    "component": component
                }
            )
        except Exception as e:
            # Log error but don't block download on history save failure
            print(f"Warning: Failed to save monitoring history: {e}")
        
        # Block download if monitoring check failed
        if not monitoring_result.is_allowed():
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "DownloadBlocked",
                    "message": "Artifact failed security monitoring check",
                    "monitoring": monitoring_result.to_dict()
                }
            )

    s3_key = S3Client.key_from_uri(pkg.s3_uri)

    if component:
        if s3_key.endswith(".zip"):
            comp_key = s3_key[:-4] + f"_{component}.zip"
        else:
            comp_key = s3_key + f"_{component}.zip"
        try:
            body = s3.download_stream(comp_key)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Component '{component}' not found")
        return StreamingResponse(body, media_type="application/octet-stream")

    try:
        body = s3.download_stream(s3_key)
    except Exception:
        raise HTTPException(status_code=404, detail="S3 object not found")
    return StreamingResponse(body, media_type="application/zip")


@app.put("/packages/{pkg_id}", response_model=PackageOut)
async def replace_package(
    pkg_id: int,
    name: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    pkg = get_package(db, pkg_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    meta = None
    if metadata:
        try:
            meta = json.loads(metadata)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    upd = PackageUpdate(name=name, version=version, metadata=meta)

    if file:
        key = f"packages/{pkg.id}/{uuid.uuid4().hex}_{file.filename}"
        try:
            s3_uri = s3.upload_fileobj(file.file, key)
            if pkg.s3_uri:
                try:
                    old_key = S3Client.key_from_uri(pkg.s3_uri)
                    s3.delete_object(old_key)
                except Exception:
                    pass
            pkg.s3_uri = s3_uri
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to upload replacement file to S3")

    try:
        pkg = update_package(db, pkg, upd)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Failed to update package metadata")

    return pkg


@app.delete("/packages/{pkg_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_package(pkg_id: int, db: Session = Depends(get_db)):
    pkg = get_package(db, pkg_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    try:
        prefix = f"packages/{pkg.id}/"
        s3.delete_prefix(prefix)
    except Exception:
        pass

    try:
        delete_package(db, pkg)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Failed to delete package from DB")

    return


@app.get("/tracks")
def get_tracks():
    """Return the list of tracks the student plans to implement"""
    return {
        "plannedTracks": [
            "Access control track"
        ]
    }


@app.delete("/reset")
def reset_registry(db: Session = Depends(get_db)):
    """Reset the registry to a system default state"""
    try:
        # Drop and recreate tables to guarantee a clean slate
        models.Base.metadata.drop_all(bind=engine)
        models.Base.metadata.create_all(bind=engine)

        # Clear S3 bucket/local dir content for package artifacts
        try:
            s3.delete_prefix("packages/")
        except Exception:
            pass

        return {"message": "Registry is reset"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset registry: {str(e)}")
