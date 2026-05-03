import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------------------------------------------------
# FIX K: Connection pool configuration
# WHAT WAS WRONG: create_engine() with no pool settings uses SQLAlchemy defaults
# (pool_size=5, max_overflow=10). On Render's free/starter Postgres tier (max 25
# connections) with multiple API workers + Celery workers, the pool is exhausted
# under any meaningful concurrent load. Dashboard goes blank mid-demo.
#
# FIX L: Redis URL unification — use DATABASE_URL env var (set by Render/Railway)
# when available, falling back to individual component vars for local dev.
# ---------------------------------------------------------------------------

# Support Render/Railway DATABASE_URL pattern (full connection string in one env var)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Cloud deployment: use the full URL directly
    # Replace postgres:// with postgresql:// (SQLAlchemy requirement)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Local dev: build from individual components
    DB_USER = os.getenv("DB_USER", "admin")
    DB_PASS = os.getenv("DB_PASS", "password123")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5433")
    DB_NAME = os.getenv("DB_NAME", "fiscalogix")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# FIX K: Conservative pool config for shared Postgres tiers
# Pool args (pool_size, max_overflow, pool_timeout) are Postgres-only;
# SQLite (used in tests via DATABASE_URL=sqlite://) rejects them.
_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
_pool_kwargs = (
    {}
    if _is_sqlite
    else dict(pool_size=5, max_overflow=5, pool_timeout=30, pool_pre_ping=True)
)
engine = create_engine(SQLALCHEMY_DATABASE_URL, **_pool_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FIX A: Import the unified Base from setup_db — not a new isolated Base
# This ensures routes and dependencies use the same metadata as the schema
from setup_db import Base


def get_db():
    """FastAPI dependency injection for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
