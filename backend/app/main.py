"""FastAPI application entry point.

Wires together:
  - routers (auth, reports, reference, admin, notifications)
  - CORS
  - static file serving for uploads
  - startup: create tables, seed reference data, train AI model if missing
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure the parent directory (project root) is importable so `from ai import ...` works
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.v1 import auth, reports, reference, admin, notifications
from app.ai_runtime import get_ai_analyzer  # re-exported for convenience


def _init_db():
    """Create tables (development convenience) and seed reference data."""
    from app.seed import run_seed
    Base.metadata.create_all(bind=engine)
    run_seed()


def _ensure_ai_model():
    """Train a model on first run if no model file exists."""
    model_path = settings.AI_MODEL_PATH
    if not os.path.exists(model_path):
        try:
            print("[main] No AI model found — training a default model...")
            from ai.train import train
            train(n_per_class=200)
            print("[main] Default AI model trained.")
        except Exception as e:
            print(f"[main] Could not train default AI model: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[main] Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.APP_ENV})")
    _init_db()
    _ensure_ai_model()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield
    print("[main] Shutting down.")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description=(
        "AI-Assisted Crowd-Sourced Community Infrastructure Damage Mapping "
        "with Severity Prioritization"
    ),
    version=settings.APP_VERSION,
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploaded images
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(reference.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["health"])
def health():
    from app.services.llm_service import get_llm_status
    return {
        "status": "healthy",
        "ai_ready": get_ai_analyzer().is_ready(),
        "llm": get_llm_status(),
        "geospatial": {"overpass_enabled": True},
    }


# Serve built React frontend if available
_FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "/app/frontend_dist")
if not os.path.isdir(_FRONTEND_DIST):
    _LOCAL_DIST = os.path.join(str(_PROJECT_ROOT), "frontend", "dist")
    if os.path.isdir(_LOCAL_DIST):
        _FRONTEND_DIST = _LOCAL_DIST

if os.path.isdir(_FRONTEND_DIST):
    print(f"[main] Serving frontend SPA from {_FRONTEND_DIST}")
    _assets_dir = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        if full_path.startswith("api/") or full_path.startswith("uploads/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        target = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}", "code": "internal_error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )
