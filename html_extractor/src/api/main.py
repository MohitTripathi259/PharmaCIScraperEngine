"""
FastAPI application for HTML extraction service.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import router
from .routes_extract import router as extract_router

# Create FastAPI app
app = FastAPI(
    title="HTML Extraction Service",
    description="Extract normalized text and rich metadata from HTML content",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(extract_router, prefix="/v1/extract", tags=["extraction"])


@app.get("/", summary="API root")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "HTML Extraction API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "extract": "/v1/extract/html",
            "health": "/v1/extract/health"
        }
    }


@app.get("/health", summary="Global health check")
async def health():
    """Global health check endpoint."""
    return {
        "status": "healthy",
        "service": "html-extraction-api"
    }
