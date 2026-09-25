"""Database engine / session / base."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _resolve_db_url(url: str) -> str:
    # Allow relative sqlite paths to resolve against backend/ cwd reliably.
    if url.startswith("sqlite:///./") or url.startswith("sqlite:///./"):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filename = url.split("sqlite:///./", 1)[1]
        return f"sqlite:///{os.path.join(base, filename)}"
    return url


DATABASE_URL = _resolve_db_url(settings.database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
