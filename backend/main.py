import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.api.v1.endpoints.jobs import job_store
from app.core.logging import configure_logging

configure_logging(settings.LOG_LEVEL)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to OfficeFlow API", "docs": "/docs"}


@app.get("/health")
def health():
    """Liveness endpoint that does not require external services."""
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/health/ready")
def readiness():
    """Readiness endpoint for local deployment and future orchestrators."""
    storage_ready = all(os.path.isdir(path) for path in (settings.UPLOAD_DIR, settings.OUTPUT_DIR))
    database = job_store.healthcheck()
    if not storage_ready:
        return {"status": "not_ready", "storage": False, "database": database}
    return {"status": "ready", "storage": True, "database": database}
