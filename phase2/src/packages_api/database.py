import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# If not set, try to construct from individual variables
if not DATABASE_URL:
    DB_USER = os.getenv("DB_USER", os.getenv("DATABASE_USER", "user"))
    DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("DATABASE_PASSWORD", "password"))
    DB_HOST = os.getenv("DB_HOST", os.getenv("DATABASE_HOST", "localhost"))
    DB_PORT = os.getenv("DB_PORT", os.getenv("DATABASE_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", os.getenv("DATABASE_NAME", "dbname"))
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Warn if using default credentials
    if DB_USER == "user" and DB_PASSWORD == "password":
        print("WARNING: Using default database credentials. Set DATABASE_URL or DB_USER/DB_PASSWORD environment variables.", file=sys.stderr)

if DATABASE_URL.startswith("sqlite"):
    # Use StaticPool + check_same_thread for SQLite in-memory testing so the
    # same in-memory database is available across connections/threads.
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============== MODELS ==============
# Define models here to ensure they use the same Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    resource = Column(String(255), nullable=True)
    resource_type = Column(String(255), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
