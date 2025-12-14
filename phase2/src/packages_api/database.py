import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool, NullPool
from sqlalchemy.sql import func

Base = declarative_base()

# Get DATABASE_URL from environment, default to SQLite for tests
DATABASE_URL = os.getenv("DATABASE_URL")

# If not set, default to in-memory SQLite (for tests) or try to construct PostgreSQL URL
if not DATABASE_URL:
    # Check if PostgreSQL credentials are explicitly provided
    DB_USER = os.getenv("DB_USER", os.getenv("DATABASE_USER"))
    DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("DATABASE_PASSWORD"))
    
    if DB_USER and DB_PASSWORD:
        # PostgreSQL credentials provided, construct PostgreSQL URL
        DB_HOST = os.getenv("DB_HOST", os.getenv("DATABASE_HOST", "localhost"))
        DB_PORT = os.getenv("DB_PORT", os.getenv("DATABASE_PORT", "5432"))
        DB_NAME = os.getenv("DB_NAME", os.getenv("DATABASE_NAME", "dbname"))
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # No credentials provided, default to SQLite in-memory for tests
        DATABASE_URL = "sqlite:///:memory:?cache=shared"
        print("INFO: No DATABASE_URL or DB credentials found, using in-memory SQLite for testing.", file=sys.stderr)

if DATABASE_URL.startswith("sqlite"):
    # In-memory: share one connection (StaticPool) across threads
    if ":memory:" in DATABASE_URL or DATABASE_URL.endswith("?mode=memory&cache=shared"):
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # File-based SQLite: open new connections per session to avoid cross-thread reuse
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
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
