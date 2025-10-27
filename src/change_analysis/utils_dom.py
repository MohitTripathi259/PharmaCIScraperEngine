"""
DOM parsing and text diff utilities.

Uses BeautifulSoup for robust HTML parsing.
Implements deterministic text extraction and diffing with difflib.
"""

from bs4 import BeautifulSoup
from difflib import SequenceMatcher, unified_diff
import re
import html
from typing import Tuple


def extract_visible_text(html_content: str) -> str:
    """
    Return normalized visible text from raw HTML.

    Args:
        html_content: HTML string

    Returns:
        Normalized visible text with collapsed whitespace

    Examples:
        >>> html = '<html><body><p>Hello</p><script>alert(1)</script><p>World</p></body></html>'
        >>> text = extract_visible_text(html)
        >>> 'Hello' in text and 'World' in text
        True
        >>> 'alert' in text
        False
    """
    if not html_content:
        return ""

    # Remove scripts/styles/comments
    soup = BeautifulSoup(html_content, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    text = soup.get_text(separator=" ")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def text_diff_stats(prev_text: str, cur_text: str) -> Tuple[int, int, int, float]:
    """
    Compute line-level diff counts and similarity ratio.

    Args:
        prev_text: Previous text content
        cur_text: Current text content

    Returns:
        Tuple of (added_count, removed_count, total_diff_lines, similarity)
        - added_count: Number of added items (words)
        - removed_count: Number of removed items (words)
        - total_diff_lines: Total number of diff lines
        - similarity: Text similarity ratio 0.0-1.0 (1.0 = identical)

    Examples:
        >>> added, removed, total, sim = text_diff_stats("Hello World", "Hello Universe")
        >>> added > 0 or removed > 0
        True
        >>> 0.0 <= sim <= 1.0
        True
        >>> sim < 1.0  # Not identical
        True

        >>> added, removed, total, sim = text_diff_stats("Same", "Same")
        >>> added == 0 and removed == 0
        True
        >>> sim == 1.0
        True
    """
    prev_lines = prev_text.split()
    cur_lines = cur_text.split()
    sm = SequenceMatcher(None, prev_lines, cur_lines)
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "insert":
            added += (j2 - j1)
        elif tag == "delete":
            removed += (i2 - i1)
    diff_lines = sum(1 for _ in unified_diff(prev_text.splitlines(), cur_text.splitlines()))
    similarity = round(sm.ratio(), 4)
    return added, removed, diff_lines, similarity


def short_context_snippets(prev_text: str, cur_text: str, max_chars: int = 1200) -> Tuple[str, str]:
    """
    Truncate both texts keeping start and end context for LLM.

    Args:
        prev_text: Previous text content
        cur_text: Current text content
        max_chars: Maximum characters per snippet (default 1200)

    Returns:
        Tuple of (prev_snippet, cur_snippet)

    Examples:
        >>> prev = "First sentence. Second sentence. Third sentence."
        >>> cur = "First sentence. New sentence. Third sentence."
        >>> prev_snip, cur_snip = short_context_snippets(prev, cur, max_chars=100)
        >>> len(prev_snip) <= 110  # Allowing for " ... " overhead
        True
        >>> len(cur_snip) <= 110
        True
    """
    def trim(t: str) -> str:
        t = t.strip()
        if len(t) <= max_chars:
            return t
        half = max_chars // 2
        return t[:half] + " ... " + t[-half:]

    return trim(prev_text), trim(cur_text)
