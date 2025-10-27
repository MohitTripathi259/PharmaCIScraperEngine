"""
FastAPI application for change analysis service.

Main application entry point. Can be run standalone or integrated
with an existing FastAPI app.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_change import router as changes_router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Change Analysis API")
    yield
    # Shutdown
    logger.info("Shutting down Change Analysis API")


# Create FastAPI app
app = FastAPI(
    title="Change Analysis API",
    description="API for detecting and analyzing web page changes with importance scoring",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(changes_router, prefix="/v1/changes")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Change Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/v1/changes/analyze",
            "health": "/v1/changes/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Global health check."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
