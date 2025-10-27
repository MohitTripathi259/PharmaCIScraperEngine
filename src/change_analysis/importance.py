"""
Importance scoring logic for change analysis.

Computes weighted importance scores based on text/visual changes,
domain context, and keyword matches.
"""

from typing import Tuple

DomainWeights = {"regulatory": 1.2, "safety": 1.15, "pricing": 1.1}


def compute_importance_score(
    text_added: int,
    text_removed: int,
    sim_text: float,
    sim_visual: float,
    goal: str,
    domain: str,
    keywords: list[str] | None = None
) -> Tuple[float, str]:
    """Combine textual+visual deltas into 0..10 importance."""
    base = (1 - sim_text) * 0.6 + (1 - sim_visual) * 0.4
    if keywords:
        key_hits = sum(1 for k in keywords if k.lower() in goal.lower())
        if key_hits:
            base += 0.05 * key_hits
    weight = DomainWeights.get(domain.lower(), 1.0)
    score = min(1.0, base * weight)
    score_10 = round(score * 10, 2)
    rationale = f"textΔ={(1-sim_text):.2f}, visΔ={(1-sim_visual):.2f}, domain={domain}, weighted={score_10}"
    return score_10, rationale


def label_from_score(score: float) -> str:
    if score < 4.5:
        return "low"
    if score < 7.5:
        return "medium"
    return "critical"


def alert_from_label(label: str) -> str:
    return {"low": "low", "medium": "med", "critical": "crit"}[label]
