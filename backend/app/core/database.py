"""Database engine, session factory, and Base model."""
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session


# Always use SQLite - read DATABASE_URL from env or default
_db_path = os.environ.get("DATABASE_URL", "sqlite:///./infraguard.db")

# Force SQLite if env var points to PostgreSQL (Render may override)
if not _db_path.startswith("sqlite"):
    _db_path = "sqlite:///./infraguard.db"
    print("[db] Forcing SQLite (PostgreSQL not supported in this build)")

print(f"[db] Using database: {_db_path}")

_db_dir = os.path.dirname(_db_path.replace("sqlite://", "").replace("sqlite:///", ""))
if _db_dir and not os.path.exists(_db_dir):
    os.makedirs(_db_dir, exist_ok=True)

engine = create_engine(
    _db_path,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
