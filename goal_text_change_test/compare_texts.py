"""
Goal-aware text change detection with numeric KPI extraction and critical phrase detection.

Compares two text documents based on a user-defined goal and outputs structured
analysis with importance scoring, similarity metrics, and key insights.

Usage:
    python compare_texts.py <goal> <prev_file> <cur_file>

Environment Variables:
    USE_BEDROCK: Set to "true" to enable Bedrock API (default: "false")
    BEDROCK_MODEL_ID: Claude model ID
    AWS_REGION: AWS region (default: us-west-2)
"""

import json
import sys
import os
import re
import base64
import io
from pathlib import Path
from datetime import datetime, timezone
import difflib
from typing import Dict, List, Tuple

# Optional boto3 import
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Optional PIL import for visual change detection
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False

from bedrock_prompt import build_universal_bedrock_prompt, coerce_json


# ============================================================================
# Visual Change Detection Helpers
# ============================================================================

def _load_image(path):
    """Load image from path, return PIL Image or None."""
    if not PIL_AVAILABLE or not path:
        return None
    try:
        img = Image.open(path)
        return img.convert("RGB")
    except Exception as e:
        print(f"[WARN] Failed to load image {path}: {e}")
        return None


def _ahash(img):
    """Compute average hash (8x8) as list of bits."""
    try:
        g = img.convert("L").resize((8, 8), Image.LANCZOS)
        px = list(g.getdata())
        avg = sum(px) / len(px)
        bits = [1 if p > avg else 0 for p in px]
        return bits
    except Exception:
        return None


def _dhash(img):
    """Compute difference hash (8x8 from 9x8) as list of bits."""
    try:
        g = img.convert("L").resize((9, 8), Image.LANCZOS)
        px = list(g.getdata())
        bits = []
        for y in range(8):
            row = [px[y * 9 + x] for x in range(9)]
            for x in range(8):
                bits.append(1 if row[x] < row[x + 1] else 0)
        return bits
    except Exception:
        return None


def _hamming(a, b):
    """Compute Hamming distance between two bit lists."""
    if not a or not b or len(a) != len(b):
        return len(a) if a else 0
    return sum((i != j) for i, j in zip(a, b))


def _sim_bits(a, b):
    """Compute similarity from two bit hashes (0..1)."""
    if not a or not b:
        return 1.0
    return max(0.0, 1.0 - _hamming(a, b) / len(a))


def _rms_similarity(a, b):
    """Compute RMS-based grayscale similarity (64x64)."""
    try:
        g1 = a.convert("L").resize((64, 64), Image.LANCZOS)
        g2 = b.convert("L").resize((64, 64), Image.LANCZOS)
        p1 = list(g1.getdata())
        p2 = list(g2.getdata())
        mse = sum((x - y) * (x - y) for x, y in zip(p1, p2)) / len(p1)
        rmse = mse ** 0.5
        return max(0.0, 1.0 - rmse / 255.0)
    except Exception:
        return None


def _visual_similarity(img_prev, img_cur):
    """
    Compute combined visual similarity from three metrics.

    Returns float in [0..1] or None if computation fails.
    Combines: 0.5*aHash + 0.3*dHash + 0.2*RMS
    """
    try:
        ah = _sim_bits(_ahash(img_prev), _ahash(img_cur))
        dh = _sim_bits(_dhash(img_prev), _dhash(img_cur))
        rm = _rms_similarity(img_prev, img_cur)

        if ah is None or dh is None or rm is None:
            return None

        combined = 0.5 * ah + 0.3 * dh + 0.2 * rm
        return max(0.0, min(1.0, combined))
    except Exception:
        return None


def _encode_image_b64(img, media_type="image/png", max_side=512):
    """
    Encode PIL Image to base64 string for Bedrock.

    Downscales to max_side if needed to keep payload small.
    Returns (base64_string, media_type) or (None, None) on error.
    """
    try:
        # Downscale if needed
        w, h = img.size
        scale = max(w, h) / float(max_side) if max(w, h) > max_side else 1.0
        if scale > 1.0:
            new_w = int(w / scale)
            new_h = int(h / scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        fmt = "PNG" if media_type.endswith("png") else "JPEG"
        img.save(buf, format=fmt, optimize=True)
        b64_str = base64.b64encode(buf.getvalue()).decode("ascii")
        return b64_str, media_type
    except Exception as e:
        print(f"[WARN] Failed to encode image: {e}")
        return None, None


# ============================================================================
# Text Analysis Functions
# ============================================================================

def extract_numbers_with_labels(text: str) -> Dict[str, float]:
    """
    Extract numeric KPIs with context labels from clinical/regulatory text.

    Captures: Enrollment, Sites, SAE%, R&D$, Phase, Protocol version, etc.
    Uses regex for numbers and nearby label detection (±5 words).

    Args:
        text: Input document text

    Returns:
        Dict mapping label → numeric value
    """
    kpis = {}
    text_lower = text.lower()

    # Phase detection - look for main study phase in overview/first paragraph
    # Prioritize early mentions (study overview) over later mentions (timelines)
    overview_match = re.search(r'(?:study|trial|clinical\s+trial)[^.]*?phase\s*(?:iii|3|ii|2|iv|4|i|1)', text_lower[:500])
    if overview_match:
        overview_text = overview_match.group().lower()
        if 'phase iii' in overview_text or 'phase 3' in overview_text:
            kpis['Phase'] = 3.0
        elif 'phase ii' in overview_text or 'phase 2' in overview_text:
            kpis['Phase'] = 2.0
        elif 'phase iv' in overview_text or 'phase 4' in overview_text:
            kpis['Phase'] = 4.0
        elif re.search(r'phase\s*i(?!\s*(?:i|v))', overview_text):
            kpis['Phase'] = 1.0

    # Protocol version (v1.0, version 1.1, etc.)
    proto_match = re.search(r'(?:protocol\s+)?v(?:ersion\s+)?(\d+\.\d+)', text_lower)
    if proto_match:
        kpis['Protocol'] = float(proto_match.group(1))

    # Enrollment / enrolled patients
    enroll_match = re.search(r'(?:enrolled?|enrollment)[\s:]+(\d+(?:,\d{3})*)\s*(?:patients?)?', text_lower)
    if enroll_match:
        num_str = enroll_match.group(1).replace(',', '')
        kpis['Enrollment'] = float(num_str)

    # Target enrollment
    target_match = re.search(r'target\s+enrollment[\s:]+(\d+(?:,\d{3})*)', text_lower)
    if target_match:
        num_str = target_match.group(1).replace(',', '')
        kpis['Target Enrollment'] = float(num_str)

    # Sites / active sites
    sites_match = re.search(r'(?:active\s+)?sites?[\s:]+(\d+)', text_lower)
    if sites_match:
        kpis['Sites'] = float(sites_match.group(1))

    # SAE rate / percentage
    sae_match = re.search(r'(?:sae|serious\s+adverse\s+events?)[^%]{0,50}?(\d+(?:\.\d+)?)%', text_lower)
    if sae_match:
        kpis['SAE'] = float(sae_match.group(1))

    # Adverse event rate
    ae_match = re.search(r'adverse\s+event\s+rate[\s:]+(\d+(?:\.\d+)?)%', text_lower)
    if ae_match:
        kpis['Adverse Event Rate'] = float(ae_match.group(1))

    # R&D investment (billions/millions)
    rd_match = re.search(r'r&d\s+investment.*?[\$](\d+(?:\.\d+)?)\s*(billion|b|million|m)', text_lower)
    if rd_match:
        value = float(rd_match.group(1))
        unit = rd_match.group(2).lower()
        if 'b' in unit:
            kpis['R&D'] = value  # Store in billions
        elif 'm' in unit:
            kpis['R&D'] = value / 1000.0  # Convert to billions

    # Program cost
    cost_match = re.search(r'program\s+cost.*?[\$](\d+(?:,\d{3})*(?:\.\d+)?)\s*(billion|million|m)', text_lower)
    if cost_match:
        num_str = cost_match.group(1).replace(',', '')
        value = float(num_str)
        unit = cost_match.group(2).lower()
        if 'm' in unit:
            kpis['Program Cost'] = value  # Store in millions

    return kpis


def detect_critical_phrases(prev_text: str, cur_text: str) -> List[str]:
    """
    Detect critical regulatory/clinical phrases appearing in current but not previous.

    Args:
        prev_text: Previous document text
        cur_text: Current document text

    Returns:
        List of detected critical phrases
    """
    critical_terms = [
        "fast track", "breakthrough", "discontinued", "terminated", "recall",
        "regulatory submission", "protocol v1.1", "phase 3", "phase iii",
        "paused", "delay", "hold", "accelerated approval", "priority review"
    ]

    prev_lower = prev_text.lower()
    cur_lower = cur_text.lower()

    detected = []
    for term in critical_terms:
        if term in cur_lower and term not in prev_lower:
            detected.append(term.title())

    return detected


def compute_goal_keywords(goal: str) -> List[str]:
    """Extract keywords from goal (words ≥3 chars)."""
    return [w for w in re.findall(r'\b\w{3,}\b', goal.lower())]


def count_keyword_hits(goal_keywords: List[str], text: str, numeric_insights: List[str]) -> int:
    """Count goal keyword occurrences in text and numeric insights."""
    combined = (text + ' ' + ' '.join(numeric_insights)).lower()
    return sum(1 for kw in goal_keywords if kw in combined)


def compute_numeric_delta(prev_kpis: Dict[str, float], cur_kpis: Dict[str, float]) -> Tuple[float, List[str]]:
    """
    Compute normalized numeric delta and generate insight strings.

    Returns:
        (mean_normalized_delta, list_of_insight_strings)
    """
    insights = []
    deltas = []

    for key in sorted(set(prev_kpis.keys()) & set(cur_kpis.keys())):
        prev_val = prev_kpis[key]
        cur_val = cur_kpis[key]

        if abs(prev_val - cur_val) > 0.01:  # Meaningful difference
            # Normalized delta
            denominator = max(abs(prev_val), abs(cur_val), 1.0)
            delta = abs(cur_val - prev_val) / denominator
            deltas.append(delta)

            # Generate insight string
            if key == 'Phase':
                insights.append(f"Phase {int(prev_val)} → {int(cur_val)}")
            elif key == 'Protocol':
                insights.append(f"Protocol v{prev_val:.1f} → v{cur_val:.1f}")
            elif key == 'Enrollment':
                insights.append(f"Enrollment {int(prev_val)} → {int(cur_val)}")
            elif key == 'Sites':
                insights.append(f"Sites {int(prev_val)} → {int(cur_val)}")
            elif key == 'SAE':
                insights.append(f"SAE {prev_val:.1f}% → {cur_val:.1f}%")
            elif key == 'Adverse Event Rate':
                insights.append(f"Adverse Event Rate {prev_val:.1f}% → {cur_val:.1f}%")
            elif key == 'R&D':
                insights.append(f"R&D ${prev_val:.1f}B → ${cur_val:.1f}B")
            elif key == 'Program Cost':
                insights.append(f"Program Cost ${int(prev_val)}M → ${int(cur_val)}M")
            else:
                insights.append(f"{key} {prev_val} → {cur_val}")

    mean_delta = (sum(deltas) / len(deltas)) if deltas else 0.0
    return mean_delta, insights


def recalibrated_scoring(
    similarity: float,
    mean_numeric_delta: float,
    keyword_hits: int,
    critical_flags: List[str],
    goal_alignment: float,
    goal: str
) -> Tuple[float, str, str]:
    """
    Compute importance score using recalibrated formula.

    Formula:
        text_term = (1 - similarity) * 0.55
        num_term = min(1.0, mean_numeric_delta) * 0.25
        kw_term = min(1.0, keyword_hits/5) * 0.10
        crit_term = (1.0 if critical_flags else 0.0) * 0.10
        align_term = goal_alignment * 0.05
        score = 10 * (text_term + num_term + kw_term + crit_term + align_term)

    Domain multiplier: 1.3x if goal contains regulatory/trial/safety keywords

    Returns:
        (import_score, importance, alert_criteria)
    """
    text_term = (1 - similarity) * 0.55
    num_term = min(1.0, mean_numeric_delta) * 0.25
    kw_term = min(1.0, keyword_hits / 5.0) * 0.10
    crit_term = (1.0 if critical_flags else 0.0) * 0.10
    align_term = goal_alignment * 0.05

    base_score = text_term + num_term + kw_term + crit_term + align_term
    score = 10.0 * base_score

    # Domain multiplier
    goal_lower = goal.lower()
    if any(kw in goal_lower for kw in ['regulatory', 'trial', 'safety', 'clinical']):
        score *= 1.3

    score = min(10.0, score)

    # Classification
    if score < 4.5:
        importance = "low"
        alert = "low"
    elif score < 7.0:
        importance = "medium"
        alert = "med"
    else:
        importance = "critical"
        alert = "crit"

    return round(score, 2), importance, alert


def enhanced_diff_analysis(goal: str, prev_text: str, cur_text: str) -> dict:
    """
    Enhanced local fallback with numeric KPI extraction and critical phrase detection.
    """
    print("[INFO] Using enhanced local fallback analysis")

    # 1. Token-level diff (keep existing)
    prev_tokens = prev_text.split()
    cur_tokens = cur_text.split()

    diff = difflib.ndiff(prev_tokens, cur_tokens)
    added = removed = 0
    for line in diff:
        if line.startswith('+ '):
            added += 1
        elif line.startswith('- '):
            removed += 1

    # Similarity ratio
    matcher = difflib.SequenceMatcher(None, prev_text, cur_text)
    similarity = round(matcher.ratio(), 4)

    # Diff lines count
    diff_lines = sum(1 for _ in difflib.unified_diff(
        prev_text.splitlines(), cur_text.splitlines()
    ))

    # 2. Numeric KPI extraction (NEW)
    prev_kpis = extract_numbers_with_labels(prev_text)
    cur_kpis = extract_numbers_with_labels(cur_text)
    mean_numeric_delta, numeric_insights = compute_numeric_delta(prev_kpis, cur_kpis)

    # 3. Critical phrases (NEW)
    critical_flags = detect_critical_phrases(prev_text, cur_text)

    # 4. Goal-aware keyword hits (NEW)
    goal_keywords = compute_goal_keywords(goal)
    keyword_hits = count_keyword_hits(goal_keywords, prev_text + cur_text, numeric_insights)

    # 5. Recalibrated scoring (NEW)
    goal_alignment = 0.5  # Default for fallback (no LLM)
    import_score, importance, alert = recalibrated_scoring(
        similarity, mean_numeric_delta, keyword_hits, critical_flags, goal_alignment, goal
    )

    # 6. Enhanced summary (NEW)
    summary_parts = []

    # Add numeric insights
    if numeric_insights:
        summary_parts.append("Key changes: " + ", ".join(numeric_insights[:4]))

    # Add critical flags
    if critical_flags:
        summary_parts.append("Critical updates: " + ", ".join(critical_flags[:3]))

    # Add token summary
    summary_parts.append(f"{added} tokens added, {removed} removed; similarity={similarity:.2%}")

    summary_change = ". ".join(summary_parts) + "."

    # 7. Key insights (NEW) - combine numeric + critical
    key_insights = numeric_insights + critical_flags
    key_insights = list(dict.fromkeys(key_insights))  # Deduplicate
    key_insights = key_insights[:8]  # Limit to 8

    if not key_insights:
        key_insights = ["Minor or no changes detected"]

    has_change = (added + removed > 0) or (similarity < 0.98) or bool(critical_flags)

    return {
        "has_change": has_change,
        "summary_change": summary_change[:500],
        "text_added": added,
        "text_removed": removed,
        "similarity": similarity,
        "total_diff_lines": diff_lines,
        "importance": importance,
        "import_score": import_score,
        "alert_criteria": alert,
        "key_insights": key_insights,
        "goal_alignment": goal_alignment,
        "reasoning": f"Enhanced analysis: text dissimilarity={1-similarity:.2%}, numeric delta={mean_numeric_delta:.2f}, keyword hits={keyword_hits}, critical flags={len(critical_flags)}",
        "llm_used": False,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat()
    }


def run_bedrock_analysis(goal: str, prev_text: str, cur_text: str, visual_ctx: dict | None = None) -> dict:
    """
    Run goal-aware analysis using AWS Bedrock Claude model.
    Merges LLM results with local metrics for comprehensive output.

    Args:
        goal: Monitoring objective
        prev_text: Previous text content
        cur_text: Current text content
        visual_ctx: Optional visual context dict from visual similarity computation
    """
    if not BOTO3_AVAILABLE:
        print("[WARN] boto3 not available, using fallback")
        return enhanced_diff_analysis(goal, prev_text, cur_text)

    use_bedrock = os.getenv("USE_BEDROCK", "false").lower() == "true"
    if not use_bedrock:
        print("[INFO] USE_BEDROCK not set to 'true', using fallback")
        return enhanced_diff_analysis(goal, prev_text, cur_text)

    try:
        model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
        region = os.getenv("AWS_REGION", "us-west-2")

        print(f"[INFO] Connecting to AWS Bedrock in {region}")
        print(f"[INFO] Using model: {model_id}")

        client = boto3.client("bedrock-runtime", region_name=region)
        payload = build_universal_bedrock_prompt(goal, prev_text, cur_text, visual_ctx=visual_ctx)

        print("[INFO] Invoking Bedrock model...")

        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8")
        )

        body = json.loads(response["body"].read())
        response_text = body["content"][0]["text"]

        print("[INFO] Parsing response...")

        llm_result = coerce_json(response_text)

        # Get local metrics for merging
        local_result = enhanced_diff_analysis(goal, prev_text, cur_text)

        # Merge: prefer LLM for summary, insights, goal_alignment; keep local metrics
        merged = {
            "has_change": llm_result.get("has_change", local_result["has_change"]),
            "summary_change": llm_result.get("summary_change", local_result["summary_change"]),
            "text_added": local_result["text_added"],  # Always use local
            "text_removed": local_result["text_removed"],  # Always use local
            "similarity": llm_result.get("similarity", local_result["similarity"]),
            "total_diff_lines": local_result["total_diff_lines"],
            "key_insights": llm_result.get("key_insights", local_result["key_insights"]),
            "goal_alignment": llm_result.get("goal_alignment", local_result["goal_alignment"]),
            "llm_used": True,
            "model_id": model_id,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Recompute score using recalibrated formula with LLM goal_alignment
        prev_kpis = extract_numbers_with_labels(prev_text)
        cur_kpis = extract_numbers_with_labels(cur_text)
        mean_numeric_delta, _ = compute_numeric_delta(prev_kpis, cur_kpis)
        critical_flags = detect_critical_phrases(prev_text, cur_text)
        goal_keywords = compute_goal_keywords(goal)
        keyword_hits = count_keyword_hits(goal_keywords, prev_text + cur_text, [])

        import_score, importance, alert = recalibrated_scoring(
            merged["similarity"],
            mean_numeric_delta,
            keyword_hits,
            critical_flags,
            merged["goal_alignment"],
            goal
        )

        merged["import_score"] = import_score
        merged["importance"] = importance
        merged["alert_criteria"] = alert
        merged["reasoning"] = llm_result.get("reasoning", local_result["reasoning"])

        print("[SUCCESS] Bedrock analysis complete")
        return merged

    except Exception as e:
        print(f"[ERROR] Bedrock analysis failed: {e}")
        print("[INFO] Falling back to local analysis")
        return enhanced_diff_analysis(goal, prev_text, cur_text)


def main():
    """Main entry point for command-line execution with optional visual change detection."""
    if len(sys.argv) < 4:
        print("=" * 80)
        print("Goal-Aware Text Change Detector (Enhanced)")
        print("=" * 80)
        print("\nUsage:")
        print("  python compare_texts.py <goal> <prev_file> <cur_file> [--prev-ss <path>] [--cur-ss <path>]")
        print("\nExample:")
        print('  python compare_texts.py "Monitor regulatory updates" prev.txt cur.txt')
        print('  python compare_texts.py "Detect UI changes" prev.txt cur.txt --prev-ss prev.png --cur-ss cur.png')
        print("\nEnvironment Variables:")
        print("  USE_BEDROCK=true              Enable AWS Bedrock")
        print("  AWS_REGION=...                AWS region")
        print("  INCLUDE_IMAGES_FOR_LLM=true   Send images to Bedrock (requires USE_BEDROCK)")
        print("  VISUAL_WEIGHT=0.3             Weight for visual similarity (0.0-0.5, default 0.3)")
        print("=" * 80)
        sys.exit(1)

    # Parse CLI arguments
    goal = sys.argv[1]
    prev_path = Path(sys.argv[2])
    cur_path = Path(sys.argv[3])

    # Parse optional image arguments
    prev_ss_path = None
    cur_ss_path = None
    i = 4
    while i < len(sys.argv):
        if sys.argv[i] == "--prev-ss" and i + 1 < len(sys.argv):
            prev_ss_path = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--cur-ss" and i + 1 < len(sys.argv):
            cur_ss_path = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not prev_path.exists():
        print(f"[ERROR] Previous file not found: {prev_path}")
        sys.exit(1)

    if not cur_path.exists():
        print(f"[ERROR] Current file not found: {cur_path}")
        sys.exit(1)

    print("=" * 80)
    print("Goal-Aware Text Change Detection (Enhanced)")
    print("=" * 80)
    print(f"Goal: {goal}")
    print(f"Previous: {prev_path}")
    print(f"Current: {cur_path}")
    if prev_ss_path:
        print(f"Previous Screenshot: {prev_ss_path}")
    if cur_ss_path:
        print(f"Current Screenshot: {cur_ss_path}")
    print("=" * 80)

    try:
        prev_text = prev_path.read_text(encoding="utf-8", errors="ignore")
        cur_text = cur_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR] Failed to read files: {e}")
        sys.exit(1)

    print(f"[INFO] Read {len(prev_text)} chars from previous file")
    print(f"[INFO] Read {len(cur_text)} chars from current file")
    print()

    # Visual similarity pipeline (optional)
    visual_used = False
    visual_similarity = None
    img_prev = None
    img_cur = None

    if prev_ss_path and cur_ss_path:
        if not PIL_AVAILABLE:
            print("[WARN] PIL not available, skipping visual analysis")
        else:
            print("[INFO] Loading images for visual analysis...")
            img_prev = _load_image(prev_ss_path)
            img_cur = _load_image(cur_ss_path)

            if img_prev and img_cur:
                print("[INFO] Computing visual similarity...")
                visual_similarity = _visual_similarity(img_prev, img_cur)
                if visual_similarity is not None:
                    visual_used = True
                    print(f"[INFO] Visual similarity: {visual_similarity:.4f}")
                else:
                    print("[WARN] Visual similarity computation failed")
            else:
                print("[WARN] Failed to load one or both images")

    # Build visual context for Bedrock (if applicable)
    visual_ctx = None
    if visual_used:
        include_images = os.getenv("INCLUDE_IMAGES_FOR_LLM", "false").lower() == "true"
        visual_summary = f"visual_similarity={visual_similarity:.2f}"

        prev_b64 = None
        cur_b64 = None
        media_type = "image/png"

        if include_images and img_prev and img_cur:
            print("[INFO] Encoding images for Bedrock...")
            prev_b64, media_type = _encode_image_b64(img_prev, media_type="image/png")
            cur_b64, _ = _encode_image_b64(img_cur, media_type="image/png")
            if not prev_b64 or not cur_b64:
                print("[WARN] Failed to encode images, proceeding without image attachment")
                include_images = False

        visual_ctx = {
            "visual_summary": visual_summary,
            "visual_similarity": visual_similarity,
            "include_images": include_images,
            "prev_image_b64": prev_b64,
            "cur_image_b64": cur_b64,
            "media_type": media_type
        }

    # Run analysis
    result = run_bedrock_analysis(goal, prev_text, cur_text, visual_ctx=visual_ctx)

    # Post-process result with visual blending (if applicable)
    if visual_used:
        # Get visual weight from env (clamped to [0.0, 0.5])
        vw = float(os.getenv("VISUAL_WEIGHT", "0.3"))
        vw = max(0.0, min(0.5, vw))

        # Blend text similarity with visual similarity
        text_sim = result.get("similarity", 0.0)
        sim_combined = (1.0 - vw) * text_sim + vw * visual_similarity

        # Recompute import_score based on combined similarity
        import_score = min(10.0, round((1.0 - sim_combined) * 10.0, 2))

        # Recompute importance and alert
        if import_score < 4.5:
            importance = "low"
            alert = "low"
        elif import_score < 7.0:
            importance = "medium"
            alert = "med"
        else:
            importance = "critical"
            alert = "crit"

        # Update result
        result["import_score"] = import_score
        result["importance"] = importance
        result["alert_criteria"] = alert

        # Prefix summary with visual note
        vsim_level = "minor" if visual_similarity > 0.85 else ("moderate" if visual_similarity > 0.65 else "significant")
        visual_prefix = f"[visual] similarity={visual_similarity:.2f} ({vsim_level}) — "

        # Prepend to existing summary
        existing_summary = result.get("summary_change", "")
        result["summary_change"] = visual_prefix + existing_summary

        # Add visual diagnostics
        result["visual_used"] = True
        result["visual_similarity"] = visual_similarity
        result["visual_method"] = "ahash+dhash+rms"
    else:
        # No visuals used
        result["visual_used"] = False

    print()
    print("=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    # Windows-safe JSON output with ASCII encoding
    try:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except UnicodeEncodeError:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    print("=" * 80)


if __name__ == "__main__":
    main()
