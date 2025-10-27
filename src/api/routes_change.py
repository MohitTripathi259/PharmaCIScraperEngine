"""
FastAPI routes for change analysis API.

Provides HTTP endpoints for analyzing web page changes.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from change_analysis import analyze_change, from_api_payload, ChangeResult


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="",
    tags=["change-analysis"]
)


@router.post("/analyze", response_model=ChangeResult)
async def analyze_change_endpoint(payload: dict[str, Any]) -> ChangeResult:
    """
    Analyze changes between two web page states.

    Request body:
        {
            "prev_dom": "string",
            "cur_dom": "string",
            "prev_ss": "string or bytes (base64 data URI or file path)",
            "cur_ss": "string or bytes",
            "goal": "string",
            "domain": "string",
            "url": "string",
            "keywords": ["string"] (optional)
        }

    Returns:
        ChangeResult with comprehensive analysis including:
        - has_change: bool
        - text_added: int
        - text_removed: int
        - similarity: float (0-1)
        - total_diff_lines: int
        - summary_change: str
        - importance: "low" | "medium" | "critical"
        - import_score: float (0-10)
        - alert_criteria: "low" | "med" | "crit"

    Raises:
        422: Validation error if payload is invalid
        500: Internal server error during analysis
    """
    try:
        # Validate and parse input
        change_input = from_api_payload(payload)

        logger.info(f"Analyzing change for URL: {change_input.url}")

        # Perform analysis
        result = analyze_change(
            prev_dom=change_input.prev_dom,
            cur_dom=change_input.cur_dom,
            prev_ss=change_input.prev_ss,
            cur_ss=change_input.cur_ss,
            goal=change_input.goal,
            domain=change_input.domain,
            url=change_input.url,
            keywords=change_input.keywords
        )

        logger.info(
            f"Analysis complete for {change_input.url}: "
            f"importance={result.importance}, score={result.import_score}"
        )

        return result

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid input: {e}"
        )

    except Exception as e:
        logger.error(f"Error analyzing change: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during analysis: {str(e)}"
        )


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Status message
    """
    return {"status": "healthy", "service": "change-analysis"}
