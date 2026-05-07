from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import Base, engine
from app.api.routes import workout

# ---------------------------------------------------------------------------
# Lifespan: runs setup before the server starts, teardown on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Creates all SQLAlchemy-mapped tables in the SQLite database if they
    don't already exist. Safe to run on every startup — it's a no-op when
    tables are already present (checkfirst=True is the default).
    """
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown logic can go here (e.g. closing connection pools)

# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="An API that uses Groq AI to extract structured fitness data and persists it to SQLite.",
    lifespan=lifespan   # replaces the deprecated @app.on_event("startup") pattern
)

# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------

app.include_router(workout.router, prefix="/api")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def health_check():
    """Confirms the server is running and returns basic metadata."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.API_VERSION
    }