"""
FastAPI routes for HTML extraction endpoint.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from change_analysis.html_extractor import (
    extract_text_and_metadata,
    HtmlExtractionResult
)

# Create router
router = APIRouter(tags=["extraction"])


class HtmlExtractionRequest(BaseModel):
    """Request model for HTML extraction."""
    html: str = Field(..., description="Raw HTML content to extract")
    base_url: Optional[str] = Field(None, description="Base URL for absolutizing links/images")
    url: Optional[str] = Field(None, description="URL of the page for context")
    max_links: Optional[int] = Field(50, ge=1, le=200, description="Maximum number of links to collect")
    max_images: Optional[int] = Field(50, ge=1, le=200, description="Maximum number of images to collect")
    model_config = {"extra": "forbid"}


@router.post(
    "/html",
    response_model=HtmlExtractionResult,
    summary="Extract text and metadata from HTML",
    description="""
    Extract normalized visible text and rich metadata from HTML content.

    Returns:
    - Normalized, paragraph-preserving text
    - Rich metadata (title, description, canonical, OG/Twitter tags, etc.)
    - Statistics (word count, links, images, etc.)

    Features:
    - Absolutizes links/images using base_url
    - Extracts dates, authors, keywords
    - Collects JSON-LD structured data
    - Handles malformed HTML gracefully
    """
)
async def extract_html(request: HtmlExtractionRequest) -> HtmlExtractionResult:
    """
    Extract text and metadata from HTML.

    Args:
        request: HtmlExtractionRequest with HTML and options

    Returns:
        HtmlExtractionResult with text, metadata, and stats
    """
    try:
        result = extract_text_and_metadata(
            html_content=request.html,
            base_url=request.base_url,
            url_for_context=request.url,
            max_links=request.max_links or 50,
            max_images=request.max_images or 50
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract HTML: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for extraction service",
    description="Check if the HTML extraction service is operational"
)
async def health_check():
    """Health check endpoint for extraction service."""
    return {
        "status": "healthy",
        "service": "html-extraction",
        "version": "1.0.0"
    }
