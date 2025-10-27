"""
Unit tests for change_analysis module.

Tests core functionality without LLM calls (USE_BEDROCK=false).
Tests are deterministic and should complete in <2s.
"""

import io
import os
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from change_analysis import analyze_change, ChangeResult
from change_analysis.utils_image import (
    load_image, ahash, dhash, hamming, perceptual_similarity
)
from change_analysis.utils_dom import (
    extract_visible_text, text_diff_stats, short_context_snippets
)
from change_analysis.importance import (
    compute_importance_score, label_from_score, alert_from_label
)


# Ensure LLM is disabled for tests
os.environ["USE_BEDROCK"] = "false"


class TestImageUtils:
    """Test image processing utilities."""

    def test_load_image_from_bytes(self):
        """Test loading image from raw bytes."""
        img = Image.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)

        loaded = load_image(buf.getvalue())
        assert isinstance(loaded, Image.Image)
        assert loaded.size == (100, 100)

    def test_load_image_from_data_uri(self):
        """Test loading image from base64 data URI."""
        img = Image.new("RGB", (50, 50), color="red")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)

        import base64
        b64 = base64.b64encode(buf.getvalue()).decode()
        data_uri = f"data:image/png;base64,{b64}"

        loaded = load_image(data_uri)
        assert isinstance(loaded, Image.Image)
        assert loaded.size == (50, 50)

    def test_ahash_identical_images(self):
        """Test that identical images have same aHash."""
        img1 = Image.new("RGB", (100, 100), color="blue")
        img2 = Image.new("RGB", (100, 100), color="blue")

        hash1 = ahash(img1)
        hash2 = ahash(img2)

        assert hash1 == hash2
        assert isinstance(hash1, int)

    def test_dhash_identical_images(self):
        """Test that identical images have same dHash."""
        img1 = Image.new("RGB", (100, 100), color="green")
        img2 = Image.new("RGB", (100, 100), color="green")

        hash1 = dhash(img1)
        hash2 = dhash(img2)

        assert hash1 == hash2
        assert isinstance(hash1, int)

    def test_hamming_distance(self):
        """Test Hamming distance calculation."""
        assert hamming(0b1010, 0b1100) == 2
        assert hamming(0, 0) == 0
        assert hamming(15, 0) == 4
        assert hamming(0xFF, 0x00) == 8

    def test_perceptual_similarity_identical(self):
        """Test perceptual similarity for identical images."""
        img1 = Image.new("RGB", (100, 100), color="yellow")
        img2 = Image.new("RGB", (100, 100), color="yellow")

        sim = perceptual_similarity(img1, img2)

        assert 0.99 <= sim <= 1.0
        assert isinstance(sim, float)

    def test_perceptual_similarity_different(self):
        """Test perceptual similarity for different images."""
        # Create images with actual patterns (not solid colors)
        img1 = Image.new("RGB", (100, 100), color="white")
        draw1 = ImageDraw.Draw(img1)
        draw1.rectangle([10, 10, 40, 40], fill="black")
        draw1.rectangle([60, 60, 90, 90], fill="black")

        img2 = Image.new("RGB", (100, 100), color="black")
        draw2 = ImageDraw.Draw(img2)
        draw2.rectangle([10, 60, 40, 90], fill="white")
        draw2.rectangle([60, 10, 90, 40], fill="white")

        sim = perceptual_similarity(img1, img2)

        assert 0.0 <= sim < 1.0  # Different but measurable
        assert isinstance(sim, float)

    def test_perceptual_similarity_slight_difference(self):
        """Test perceptual similarity for slightly different images."""
        # Create similar images with slight differences
        img1 = Image.new("RGB", (100, 100), color="white")
        draw1 = ImageDraw.Draw(img1)
        draw1.rectangle([20, 20, 80, 80], fill="black")

        img2 = Image.new("RGB", (100, 100), color="white")
        draw2 = ImageDraw.Draw(img2)
        draw2.rectangle([20, 20, 80, 80], fill="black")
        # Add a small difference
        draw2.rectangle([45, 45, 55, 55], fill="gray")

        sim = perceptual_similarity(img1, img2)

        assert 0.0 <= sim < 1.0  # Similar but not identical
        assert isinstance(sim, float)


class TestDOMUtils:
    """Test DOM parsing utilities."""

    def test_extract_visible_text_basic(self):
        """Test basic visible text extraction."""
        html = "<html><body><p>Hello</p><p>World</p></body></html>"
        text = extract_visible_text(html)

        assert "Hello" in text
        assert "World" in text

    def test_extract_visible_text_removes_scripts(self):
        """Test that scripts are removed from visible text."""
        html = """
        <html>
            <body>
                <p>Visible content</p>
                <script>alert('hidden');</script>
                <style>.hidden { display: none; }</style>
            </body>
        </html>
        """
        text = extract_visible_text(html)

        assert "Visible content" in text
        assert "alert" not in text
        assert "hidden" not in text.lower() or "display" not in text

    def test_text_diff_stats_identical(self):
        """Test diff stats for identical text."""
        text = "This is some text"
        added, removed, total, sim = text_diff_stats(text, text)

        assert added == 0
        assert removed == 0
        assert total == 0
        assert sim == 1.0

    def test_text_diff_stats_different(self):
        """Test diff stats for different text."""
        prev = "Trial 3 results pending"
        cur = "Trial 4 results approved"

        added, removed, total, sim = text_diff_stats(prev, cur)

        assert added > 0 or removed > 0
        assert total >= 1
        assert 0.0 < sim < 1.0

    def test_short_context_snippets(self):
        """Test context snippet generation."""
        prev = "First sentence. " * 100  # Long text
        cur = "Different sentence. " * 100

        prev_snip, cur_snip = short_context_snippets(prev, cur, max_chars=200)

        assert len(prev_snip) <= 200
        assert len(cur_snip) <= 200
        assert "First sentence" in prev_snip
        assert "Different sentence" in cur_snip


class TestImportance:
    """Test importance scoring utilities."""

    def test_compute_importance_score_basic(self):
        """Test basic importance score computation."""
        score, rationale = compute_importance_score(
            text_added=10,
            text_removed=5,
            sim_text=0.7,
            sim_visual=0.8,
            goal="Monitor changes",
            domain="general",
            keywords=None
        )

        assert 0.0 <= score <= 10.0
        assert isinstance(rationale, str)
        assert len(rationale) > 0

    def test_compute_importance_score_with_keywords(self):
        """Test importance score with keyword matching."""
        score_without, _ = compute_importance_score(
            text_added=5,
            text_removed=5,
            sim_text=0.8,
            sim_visual=0.9,
            goal="Monitor changes",
            domain="general",
            keywords=None
        )

        score_with, rationale = compute_importance_score(
            text_added=5,
            text_removed=5,
            sim_text=0.8,
            sim_visual=0.9,
            goal="Monitor pricing changes",  # keyword "pricing" in goal
            domain="general",
            keywords=["pricing", "cost"]
        )

        assert score_with > score_without  # Keyword should boost score
        assert isinstance(rationale, str)  # Rationale should be a string

    def test_compute_importance_score_domain_weight(self):
        """Test domain-specific weight multiplier."""
        score_regular, _ = compute_importance_score(
            text_added=10,
            text_removed=10,
            sim_text=0.5,
            sim_visual=0.5,
            goal="Monitor changes",
            domain="general",
            keywords=None
        )

        score_regulatory, rationale = compute_importance_score(
            text_added=10,
            text_removed=10,
            sim_text=0.5,
            sim_visual=0.5,
            goal="Monitor changes",
            domain="regulatory",
            keywords=None
        )

        assert score_regulatory > score_regular  # Regulatory should be weighted higher
        assert "regulatory" in rationale.lower()

    def test_label_from_score(self):
        """Test severity label generation."""
        assert label_from_score(3.0) == "low"
        assert label_from_score(5.5) == "medium"
        assert label_from_score(8.0) == "critical"
        assert label_from_score(0.0) == "low"
        assert label_from_score(10.0) == "critical"

    def test_alert_from_label(self):
        """Test alert level mapping."""
        assert alert_from_label("low") == "low"
        assert alert_from_label("medium") == "med"
        assert alert_from_label("critical") == "crit"


class TestAnalyzeChange:
    """Test main analyze_change function."""

    def create_test_image(self, color: str, rect: bool = False) -> bytes:
        """Helper to create test image bytes."""
        img = Image.new("RGB", (200, 200), color=color)

        if rect:
            draw = ImageDraw.Draw(img)
            draw.rectangle([80, 80, 120, 120], fill="red")

        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    def test_analyze_change_with_differences(self):
        """Test analysis with actual differences."""
        # Create different DOMs
        prev_dom = """
        <html>
            <body>
                <h1>Clinical Trial 3</h1>
                <p>Status: Pending</p>
                <p>Participants: 100</p>
            </body>
        </html>
        """

        cur_dom = """
        <html>
            <body>
                <h1>Clinical Trial 4</h1>
                <p>Status: Approved</p>
                <p>Participants: 150</p>
            </body>
        </html>
        """

        # Create different screenshots
        prev_ss = self.create_test_image("white", rect=False)
        cur_ss = self.create_test_image("white", rect=True)

        # Analyze
        result = analyze_change(
            prev_dom=prev_dom,
            cur_dom=cur_dom,
            prev_ss=prev_ss,
            cur_ss=cur_ss,
            goal="Monitor clinical trials",
            domain="regulatory",
            url="https://example.com/trials",
            keywords=["trial", "approved"]
        )

        # Assertions
        assert isinstance(result, ChangeResult)
        assert result.has_change is True
        assert result.text_added > 0 or result.text_removed > 0
        assert 0.0 <= result.similarity < 1.0
        assert result.total_diff_lines >= 1
        assert result.importance in ["low", "medium", "critical"]
        assert 0.0 <= result.import_score <= 10.0
        assert result.alert_criteria in ["low", "med", "crit"]
        assert len(result.summary_change) > 0

    def test_analyze_change_identical(self):
        """Test analysis with identical content."""
        dom = "<html><body><p>Same content</p></body></html>"
        ss = self.create_test_image("blue")

        result = analyze_change(
            prev_dom=dom,
            cur_dom=dom,
            prev_ss=ss,
            cur_ss=ss,
            goal="Monitor changes",
            domain="general",
            url="https://example.com"
        )

        # Should detect no meaningful change
        assert isinstance(result, ChangeResult)
        assert result.text_added == 0
        assert result.text_removed == 0
        assert result.similarity > 0.95  # Very similar
        assert result.total_diff_lines == 0

    def test_analyze_change_deterministic(self):
        """Test that results are deterministic when LLM is disabled."""
        prev_dom = "<html><body><p>Version A</p></body></html>"
        cur_dom = "<html><body><p>Version B</p></body></html>"
        prev_ss = self.create_test_image("red")
        cur_ss = self.create_test_image("green")

        # Run twice
        result1 = analyze_change(
            prev_dom=prev_dom,
            cur_dom=cur_dom,
            prev_ss=prev_ss,
            cur_ss=cur_ss,
            goal="Test",
            domain="general",
            url="https://example.com"
        )

        result2 = analyze_change(
            prev_dom=prev_dom,
            cur_dom=cur_dom,
            prev_ss=prev_ss,
            cur_ss=cur_ss,
            goal="Test",
            domain="general",
            url="https://example.com"
        )

        # Results should be identical
        assert result1.has_change == result2.has_change
        assert result1.text_added == result2.text_added
        assert result1.text_removed == result2.text_removed
        assert result1.similarity == result2.similarity
        assert result1.total_diff_lines == result2.total_diff_lines
        assert result1.importance == result2.importance
        assert result1.import_score == result2.import_score
        assert result1.alert_criteria == result2.alert_criteria

    def test_analyze_change_result_fields(self):
        """Test that result has all required fields."""
        prev_dom = "<html><body><p>Old</p></body></html>"
        cur_dom = "<html><body><p>New</p></body></html>"
        prev_ss = self.create_test_image("white")
        cur_ss = self.create_test_image("black")

        result = analyze_change(
            prev_dom=prev_dom,
            cur_dom=cur_dom,
            prev_ss=prev_ss,
            cur_ss=cur_ss,
            goal="Test all fields",
            domain="pricing",
            url="https://example.com/pricing"
        )

        # Check all required fields exist
        assert hasattr(result, "has_change")
        assert hasattr(result, "text_added")
        assert hasattr(result, "text_removed")
        assert hasattr(result, "similarity")
        assert hasattr(result, "total_diff_lines")
        assert hasattr(result, "summary_change")
        assert hasattr(result, "importance")
        assert hasattr(result, "import_score")
        assert hasattr(result, "alert_criteria")

        # Type checks
        assert isinstance(result.has_change, bool)
        assert isinstance(result.text_added, int)
        assert isinstance(result.text_removed, int)
        assert isinstance(result.similarity, float)
        assert isinstance(result.total_diff_lines, int)
        assert isinstance(result.summary_change, str)
        assert isinstance(result.importance, str)
        assert isinstance(result.import_score, float)
        assert isinstance(result.alert_criteria, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
