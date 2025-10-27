"""
LLM adapter for change summarization with AWS Bedrock.

Supports conditional import - only loads boto3 when USE_BEDROCK is enabled.
Provides robust JSON parsing and deterministic fallback.
"""

import os
import json
import re
from typing import Dict
from .utils_dom import short_context_snippets

USE_BEDROCK = os.getenv("USE_BEDROCK", "false").lower() == "true"
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")


def build_diff_prompt(url: str, goal: str, domain: str, prev_snippet: str, cur_snippet: str,
                      added: int, removed: int, diff_lines: int) -> str:
    """Structured prompt for LLM diff summarization."""
    return f"""
You are an expert analyst. Compare previous vs current webpage snapshots.

URL: {url}
Goal: {goal}
Domain: {domain}

Stats:
- text added: {added}
- text removed: {removed}
- total diff lines: {diff_lines}

Previous snippet:
<<<
{prev_snippet}
>>>

Current snippet:
<<<
{cur_snippet}
>>>

Respond strictly in JSON with keys:
summary_change (string)
salient_points (list)
keyword_hits (list)
"""


def summarize_with_llm(prompt: str) -> Dict | None:
    """Stub LLM call; if USE_BEDROCK=false, return None."""
    if not USE_BEDROCK:
        return None
    try:
        import boto3
        bedrock = boto3.client("bedrock-runtime")
        resp = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({"prompt": prompt, "max_tokens": 400}),
            contentType="application/json"
        )
        text = resp["body"].read().decode("utf-8")
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return None
        return json.loads(match.group(0))
    except Exception:
        return None


def local_summary_fallback(url: str, goal: str, domain: str,
                            prev_text: str, cur_text: str,
                            added: int, removed: int, diff_lines: int) -> Dict:
    """Heuristic deterministic summary."""
    change = ""
    if added and not removed:
        change = f"Added {added} new words."
    elif removed and not added:
        change = f"Removed {removed} words."
    elif added or removed:
        change = f"{added} added, {removed} removed."
    else:
        change = "Minor formatting change."
    summary = f"Content modified on {domain} page ({url}): {change} ({diff_lines} diff lines)."
    return {"summary_change": summary, "salient_points": [], "keyword_hits": []}
