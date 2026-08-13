import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from singularity.api.routes_telemetry import router as telemetry_router
from singularity.api.routes_console import router as console_router
from singularity.api.routes_media import router as media_router
from singularity.api.routes_audio import router as audio_router
from singularity.api.routes_sandbox import router as sandbox_router
from singularity.api.routes_economy import router as economy_router
from singularity.api.routes_simulations import router as simulations_router
from singularity.api.routes_temporal import router as temporal_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for the FastAPI application."""
    logger.info("C2 API matrix online")
    yield

app = FastAPI(
    title="Simulated Singularity C2 API",
    description="Constellation-Class Multi-Agent Command & Control Environment API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(telemetry_router)
app.include_router(console_router)
app.include_router(media_router)
app.include_router(audio_router)
app.include_router(sandbox_router)
app.include_router(economy_router)
app.include_router(simulations_router)
app.include_router(temporal_router)


@app.get("/api/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify the API is running."""
    return {"status": "ok"}

# Mount static files if they exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
