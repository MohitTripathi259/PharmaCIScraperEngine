"""
Bedrock prompt builder for goal-aware text change detection.

Creates prompts that enforce strict JSON output matching the required schema.
"""

import json
import re


def build_universal_bedrock_prompt(goal: str, previous_text: str, current_text: str, visual_ctx: dict | None = None) -> dict:
    """
    Build Bedrock prompt enforcing strict JSON schema output.

    Args:
        goal: Monitoring objective
        previous_text: Baseline/previous version
        current_text: New/current version
        visual_ctx: Optional visual context dict with fields:
                   - visual_summary: str (e.g., 'visual similarity 0.91 (minor)')
                   - visual_similarity: float (0..1)
                   - include_images: bool
                   - prev_image_b64: base64 string or None
                   - cur_image_b64: base64 string or None
                   - media_type: str (e.g., 'image/png')

    Returns:
        Dictionary with Bedrock API payload structure
    """
    system = (
        "You are an advanced analytical model specializing in comparative reasoning, "
        "change detection, and goal-aware interpretation. "
        "\n\n"
        "You must analyze two document versions and identify ALL relevant changes with respect to a clearly defined GOAL. "
        "Detect semantic, numerical, terminology, and structural changes. "
        "\n\n"
        "CRITICAL: Output STRICT JSON only — no markdown, no code fences, no commentary. "
        "The JSON must be valid and parseable."
    )

    # Smart truncation to keep payload ≤ 8k chars
    prev_truncated = _smart_truncate(previous_text, max_chars=3500)
    cur_truncated = _smart_truncate(current_text, max_chars=3500)

    # Build visual context section if provided
    visual_section = ""
    if visual_ctx and visual_ctx.get("visual_summary"):
        vsim = visual_ctx.get("visual_similarity")
        if vsim is not None:
            level = "minor" if vsim > 0.85 else ("moderate" if vsim > 0.65 else "significant")
            visual_section = f"""

VISUAL CONTEXT:
Visual similarity: {vsim:.2f} ({level} visual change detected)
Use this as an auxiliary signal aligned to the GOAL. Visual changes may indicate layout, formatting,
or presentation differences that complement textual changes.
"""

    user = f"""
MONITORING GOAL:
{goal}

TASK:
Compare the previous and current documents below. Identify changes relevant to the GOAL.
Focus on: additions, removals, replacements, numerical changes, terminology changes, structural changes.

PREVIOUS DOCUMENT:
{prev_truncated}

CURRENT DOCUMENT:
{cur_truncated}{visual_section}

INSTRUCTIONS:
1. Identify all meaningful changes between versions
2. Assess relevance to the GOAL
3. Extract numeric KPI changes (enrollment, sites, phase, SAE%, R&D$, protocol version)
4. Detect critical phrases (fast track, breakthrough, discontinued, terminated, phase 3, regulatory submission)
5. Evaluate importance and potential impact

OUTPUT FORMAT (respond with VALID JSON only):
{{
  "summary_change": "Structured comparative summary (200-300 chars)",
  "similarity": 0.0-1.0,
  "import_score": 0.0-10.0,
  "importance": "low|medium|critical",
  "alert_criteria": "low|med|crit",
  "key_insights": [
    "Numeric change 1 (e.g., Phase 2 → 3)",
    "Numeric change 2 (e.g., Enrollment 450 → 800)",
    "Critical phrase 1 (e.g., Fast Track received)",
    "Additional insights..."
  ],
  "goal_alignment": 0.0-1.0,
  "reasoning": "Brief justification of importance score (1-2 sentences)"
}}

FIELD REQUIREMENTS:
- summary_change: MUST follow structured comparative format with explicit before/after statements:
  * Start with most significant change: "Previous: [X], Current: [Y], Change: [significant/moderate/minor] [increase/decrease/shift]"
  * Include 2-3 key changes in "Previous → Current" format
  * Use quantitative terms when possible (percentages, absolute numbers)
  * Example: "Previous: Phase 2, enrollment 450. Current: Phase 3, enrollment 800. Significant trial progression: +78% enrollment, phase advancement. Previous SAE 2.5%, Current 3.2% (+0.7pp). Previous: no fast track status. Current: Fast track designation received."
  * Avoid vague descriptions - always specify what changed FROM and TO
- similarity: 0.0 (completely different) to 1.0 (identical)
- import_score: 0.0 (no importance) to 10.0 (critical)
- importance: "low" (<4.5), "medium" (4.5-6.9), "critical" (≥7.0)
- alert_criteria: Map importance to "low", "med", or "crit"
- key_insights: 3-8 specific observations with explicit comparisons (use → or "from X to Y" format)
- goal_alignment: 0.0 (irrelevant) to 1.0 (perfectly aligned)
- reasoning: Explain why this importance level was assigned, referencing specific changes

Respond with JSON only (no code fences, no markdown):
"""

    # Build message content
    content = []

    # Add images if requested
    if visual_ctx and visual_ctx.get("include_images"):
        prev_b64 = visual_ctx.get("prev_image_b64")
        cur_b64 = visual_ctx.get("cur_image_b64")
        media_type = visual_ctx.get("media_type", "image/png")

        if prev_b64 and cur_b64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": prev_b64
                }
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": cur_b64
                }
            })

    # Always append the text block
    content.append({"type": "text", "text": user.strip()})

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "system": system,
        "messages": [
            {"role": "user", "content": content}
        ],
        "max_tokens": 1000,
        "temperature": 0,
    }


def _smart_truncate(text: str, max_chars: int = 3500) -> str:
    """
    Truncate text preserving start and end context.

    Args:
        text: Input text
        max_chars: Maximum characters

    Returns:
        Truncated text with ellipsis if needed
    """
    text = text.strip()

    if len(text) <= max_chars:
        return text

    # Keep first 60% and last 40%
    first_part = int(max_chars * 0.6)
    last_part = int(max_chars * 0.4)

    return (
        text[:first_part] +
        "\n\n[... content truncated ...]\n\n" +
        text[-last_part:]
    )


def coerce_json(response_text: str) -> dict:
    """
    Parse Claude JSON response, handling formatting issues.

    Args:
        response_text: Raw text response from Claude

    Returns:
        Parsed JSON as dictionary

    Raises:
        json.JSONDecodeError: If response is not valid JSON after cleaning
    """
    text = response_text.strip()

    # Remove markdown code fences
    if text.startswith("```"):
        text = text.strip("`")
        # Remove language identifier line
        if "\n" in text:
            lines = text.split("\n")
            if lines[0].strip().lower() in ["json", "javascript", ""]:
                text = "\n".join(lines[1:])

    # Remove trailing code fence
    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Extract JSON if surrounded by text
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end+1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON response:")
        print(f"First 200 chars: {text[:200]}")
        print(f"Last 200 chars: {text[-200:]}")
        raise e
