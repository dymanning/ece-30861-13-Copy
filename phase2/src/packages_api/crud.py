from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas


def create_package(db: Session, pkg_in: schemas.PackageCreate) -> models.Package:
    pkg = models.Package(
        name=pkg_in.name,
        version=pkg_in.version,
        metadata_json=pkg_in.metadata,
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg


def get_package(db: Session, pkg_id: int) -> Optional[models.Package]:
    return db.query(models.Package).filter(models.Package.id == pkg_id).first()


def update_package(db: Session, pkg: models.Package, upd: schemas.PackageUpdate) -> models.Package:
    if upd.name is not None:
        pkg.name = upd.name
    if upd.version is not None:
        pkg.version = upd.version
    if upd.metadata is not None:
        pkg.metadata_json = upd.metadata
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return pkg


def delete_package(db: Session, pkg: models.Package):
    db.delete(pkg)
    db.commit()
