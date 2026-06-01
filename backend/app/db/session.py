"""SQLAlchemy database setup - local SQLite storage"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency for DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables - called on startup"""
    # Import models so they're registered with Base
    from app.models import meeting, user, transcript  # noqa
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def _run_migrations():
    """Apply additive column migrations that create_all won't handle on existing tables."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    import sqlite3, re
    db_path = re.sub(r"^sqlite:///", "", settings.DATABASE_URL)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Add transcript_s3_url to meeting_reports if it doesn't exist yet
    cur.execute("PRAGMA table_info(meeting_reports)")
    cols = {row[1] for row in cur.fetchall()}
    if "transcript_s3_url" not in cols:
        cur.execute("ALTER TABLE meeting_reports ADD COLUMN transcript_s3_url TEXT")
        conn.commit()
    conn.close()
