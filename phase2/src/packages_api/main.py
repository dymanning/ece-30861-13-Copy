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

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Packages API")
s3 = S3Client()


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


@app.get("/packages/{pkg_id}")
def download_package(
    pkg_id: int, component: Optional[str] = None, db: Session = Depends(get_db)
):
    pkg = get_package(db, pkg_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    if not pkg.s3_uri:
        raise HTTPException(status_code=404, detail="Package file not available")

    s3_key = S3Client.key_from_uri(pkg.s3_uri)

    if component:
        comp_key = s3_key.replace(".zip", f"_{component}.zip")
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

    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
