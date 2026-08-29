"""Database engine, session factory, and Base model."""
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings


# Use SQLite for local / Vercel deployment
_db_path = settings.DATABASE_URL
if _db_path.startswith("sqlite"):
    _db_dir = os.path.dirname(_db_path.replace("sqlite://", "").replace("sqlite:///", ""))
    if _db_dir and not os.path.exists(_db_dir):
        os.makedirs(_db_dir, exist_ok=True)
    engine = create_engine(
        _db_path,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG and False,
    )
else:
    engine = create_engine(
        _db_path,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.DEBUG and False,
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
