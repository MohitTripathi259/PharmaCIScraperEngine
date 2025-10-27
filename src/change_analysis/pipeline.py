"""
Main pipeline for change analysis.

Orchestrates image processing, DOM parsing, LLM summarization,
and importance scoring to produce comprehensive change results.
"""

from .schemas import ChangeResult
from .utils_image import load_image, perceptual_similarity
from .utils_dom import extract_visible_text, text_diff_stats, short_context_snippets
from .importance import compute_importance_score, label_from_score, alert_from_label
from .llm_adapter import build_diff_prompt, summarize_with_llm, local_summary_fallback


def analyze_change(prev_dom: str, cur_dom: str,
                    prev_ss, cur_ss,
                    goal: str, domain: str, url: str,
                    keywords: list[str] | None = None) -> ChangeResult:
    """Full text+visual diff pipeline."""
    # --- visual similarity ---
    prev_img = load_image(prev_ss)
    cur_img = load_image(cur_ss)
    sim_visual = perceptual_similarity(prev_img, cur_img)

    # --- textual similarity ---
    prev_text = extract_visible_text(prev_dom)
    cur_text = extract_visible_text(cur_dom)
    added, removed, diff_lines, sim_text = text_diff_stats(prev_text, cur_text)

    # --- summary (LLM or fallback) ---
    prev_snip, cur_snip = short_context_snippets(prev_text, cur_text, max_chars=800)
    prompt = build_diff_prompt(url, goal, domain, prev_snip, cur_snip, added, removed, diff_lines)
    llm_res = summarize_with_llm(prompt)
    if not llm_res:
        llm_res = local_summary_fallback(url, goal, domain, prev_text, cur_text, added, removed, diff_lines)
    summary = llm_res.get("summary_change", "")

    # --- importance scoring ---
    score_10, rationale = compute_importance_score(
        text_added=added, text_removed=removed,
        sim_text=sim_text, sim_visual=sim_visual,
        goal=goal, domain=domain, keywords=keywords or []
    )
    label = label_from_score(score_10)
    alert = alert_from_label(label)

    has_change = (added + removed > 0) or (sim_visual < 0.98)
    similarity = round((sim_text * 0.6 + sim_visual * 0.4), 4)

    return ChangeResult(
        has_change=has_change,
        text_added=added,
        text_removed=removed,
        similarity=similarity,
        total_diff_lines=diff_lines,
        summary_change=summary[:500],
        importance=label,
        import_score=score_10,
        alert_criteria=alert
    )
