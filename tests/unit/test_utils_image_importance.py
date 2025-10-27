"""
Test for utils_image and importance modules.

Verifies visual similarity and importance scoring work correctly.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from change_analysis import utils_image, importance
from PIL import Image, ImageDraw


def make_img(bg_color, rect_color):
    """Create image with background and rectangle of different colors."""
    im = Image.new("RGB", (64, 64), bg_color)
    d = ImageDraw.Draw(im)
    d.rectangle([16, 16, 48, 48], fill=rect_color)
    return im


def test_visual_similarity_and_importance():
    # Create images with contrasting patterns (white bg with black rect vs black bg with white rect)
    im1 = make_img("white", "black")
    im2 = make_img("black", "white")
    sim = utils_image.perceptual_similarity(im1, im2)
    assert 0 <= sim <= 1 and sim < 1
    score, r = importance.compute_importance_score(
        text_added=5,
        text_removed=2,
        sim_text=0.8,
        sim_visual=sim,
        goal="track trials",
        domain="regulatory",
        keywords=["trial"]
    )
    assert 0 <= score <= 10
    label = importance.label_from_score(score)
    alert = importance.alert_from_label(label)
    assert label in {"low", "medium", "critical"}
    assert alert in {"low", "med", "crit"}
