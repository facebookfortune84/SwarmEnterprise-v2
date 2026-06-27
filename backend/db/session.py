import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base


def get_db_url() -> str:
    """Get database URL from environment or default to SQLite."""
    url = os.getenv("SWARM_DB_URL")
    if url:
        return url

    # Default to SQLite if no DB URL provided
    db_dir = Path(os.getenv("SWARM_PG_DIR", Path(__file__).resolve().parents[2] / "pg_data"))
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "swarm_enterprise.db"
    return f"sqlite:///{db_path.as_posix()}"


engine = create_engine(
    get_db_url(), connect_args={"check_same_thread": False} if "sqlite" in get_db_url() else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    # Import models here to ensure they are registered with Base
    from backend.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
