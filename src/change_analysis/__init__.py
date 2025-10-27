"""
Change Analysis Package

Production-ready module for detecting and analyzing web page changes.

Main functionality:
- Visual similarity analysis using perceptual hashing (aHash/dHash)
- Text diff analysis with difflib
- LLM-powered summarization (AWS Bedrock) with deterministic fallback
- Importance scoring with domain-specific weights
- Keyword detection and alerting

Usage:
    >>> from change_analysis import analyze_change
    >>> result = analyze_change(
    ...     prev_dom="<html>...</html>",
    ...     cur_dom="<html>...</html>",
    ...     prev_ss=b"...",  # or file path or data URI
    ...     cur_ss=b"...",
    ...     goal="Monitor pricing changes",
    ...     domain="pricing",
    ...     url="https://example.com",
    ...     keywords=["price", "cost"]
    ... )
    >>> print(result.importance)
    'medium'
    >>> print(result.summary_change)
    'Content modified on pricing page: 10 lines added, 5 lines removed'
"""

from .pipeline import analyze_change
from .schemas import (
    ChangeInput,
    ChangeResult,
    Severity,
    Alert,
    from_api_payload
)

__version__ = "1.0.0"

__all__ = [
    "analyze_change",
    "ChangeInput",
    "ChangeResult",
    "Severity",
    "Alert",
    "from_api_payload",
]
