"""FastAPI application - Minimal version for testing."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from core.config import get_settings
from core.logging import setup_logging

# Get settings and setup logging
settings = get_settings()
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Seked AI Governance Platform",
    description="Complete AI governance infrastructure with revenue model",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "online", "version": "1.0.0"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Seked AI Governance Platform API", "status": "online"}

# Basic routers (minimal set for testing)
try:
    from apps.api.routers.ai_citizenship import router as ai_citizenship_router
    app.include_router(ai_citizenship_router, prefix="/api/v1", tags=["AI Citizenship"])

    from apps.api.routers.control_plane import router as control_plane_router
    app.include_router(control_plane_router, prefix="/api/v1", tags=["Control Plane"])

    from apps.api.routers.vctt import router as vctt_router
    app.include_router(vctt_router, prefix="/api/v1", tags=["VCTT"])

    from apps.api.routers.signal_coherence import router as signal_coherence_router
    app.include_router(signal_coherence_router, prefix="/api/v1", tags=["Signal Coherence"])

except ImportError as e:
    print(f"Warning: Some routers failed to load: {e}")
    # Continue without failing - allow basic health check to work

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8765)
