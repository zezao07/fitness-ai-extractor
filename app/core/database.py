from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# SQLite stores everything in a single file next to your project root.
# "check_same_thread=False" is required for SQLite when used with FastAPI,
# because FastAPI can handle a request across multiple threads.
DATABASE_URL = "sqlite:///./fitness_data.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
# autocommit=False  → we control when transactions are committed (safer)
# autoflush=False   → prevents SQLAlchemy from issuing SQL before we call commit()
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
# All ORM models inherit from this class so SQLAlchemy can track their tables.
class Base(DeclarativeBase):
    pass

# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------
def get_db():
    """
    Yields a database session for the duration of a single request,
    then guarantees the session is closed — even if an exception occurs.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()