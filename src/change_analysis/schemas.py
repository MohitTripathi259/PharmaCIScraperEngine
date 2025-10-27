"""
Pydantic v2 models for change analysis.

Defines strict input/output schemas with type validation.
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


# Type aliases for severity and alert levels
Severity = Literal["low", "medium", "critical"]
Alert = Literal["low", "med", "crit"]


class ChangeInput(BaseModel):
    """
    Input model for change analysis.

    Attributes:
        prev_dom: Previous HTML DOM as string
        cur_dom: Current HTML DOM as string
        prev_ss: Previous screenshot (bytes, base64 data URI, or file path)
        cur_ss: Current screenshot (bytes, base64 data URI, or file path)
        goal: User's monitoring goal/description
        domain: Domain category (e.g., "regulatory", "safety", "pricing")
        url: URL being monitored
        keywords: Optional list of keywords to watch for importance scoring
    """

    prev_dom: str = Field(..., description="Previous HTML DOM")
    cur_dom: str = Field(..., description="Current HTML DOM")
    prev_ss: str | bytes = Field(..., description="Previous screenshot")
    cur_ss: str | bytes = Field(..., description="Current screenshot")
    goal: str = Field(..., description="Monitoring goal")
    domain: str = Field(..., description="Domain category")
    url: str = Field(..., description="URL being monitored")
    keywords: list[str] | None = Field(default=None, description="Keywords for importance detection")

    model_config = ConfigDict(extra="forbid")


class ChangeResult(BaseModel):
    """
    Result model for change analysis.

    Attributes:
        has_change: Whether a meaningful change was detected
        text_added: Number of text lines/words added
        text_removed: Number of text lines/words removed
        similarity: Overall similarity score 0..1 (1=identical, combining text+visual)
        total_diff_lines: Total number of diff lines in text comparison
        summary_change: Natural language summary of the change
        importance: Severity label based on importance score
        import_score: Importance score 0..10
        alert_criteria: Alert level mapping from importance
    """

    has_change: bool = Field(..., description="Whether a change was detected")
    text_added: int = Field(..., ge=0, description="Number of text items added")
    text_removed: int = Field(..., ge=0, description="Number of text items removed")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Overall similarity (0=different, 1=identical)")
    total_diff_lines: int = Field(..., ge=0, description="Total diff lines")
    summary_change: str = Field(..., description="Change summary")
    importance: Severity = Field(..., description="Importance level")
    import_score: float = Field(..., ge=0.0, le=10.0, description="Importance score 0-10")
    alert_criteria: Alert = Field(..., description="Alert level")

    model_config = ConfigDict(extra="forbid")


def from_api_payload(d: dict) -> ChangeInput:
    """
    Create ChangeInput from API payload dictionary.

    Args:
        d: Dictionary from API request

    Returns:
        Validated ChangeInput instance

    Raises:
        ValidationError: If payload doesn't match schema
    """
    return ChangeInput.model_validate(d)
