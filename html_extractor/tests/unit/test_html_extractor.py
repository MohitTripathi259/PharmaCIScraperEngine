"""
Comprehensive unit tests for HTML extractor.

Tests with representative HTML snippets (no network calls).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from change_analysis.html_extractor import extract_text_and_metadata


# ============================================================================
# Test HTML Snippets
# ============================================================================

COMPLEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cancer Cachexia Research Update</title>
    <meta name="description" content="Latest findings in cancer cachexia treatment and patient outcomes.">
    <meta name="author" content="Dr. Jane Smith">
    <meta name="keywords" content="cancer, cachexia, oncology, treatment">
    <meta property="article:published_time" content="2024-01-15T10:30:00Z">
    <meta property="article:modified_time" content="2024-01-20T14:45:00Z">
    <meta property="og:title" content="Cancer Cachexia Research Update">
    <meta property="og:description" content="Breakthrough findings in cancer cachexia treatment approaches.">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="Medical Research Portal">
    <meta property="og:image" content="/images/research-hero.jpg">
    <meta property="og:url" content="https://example.com/research/cachexia">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Cancer Cachexia Research">
    <meta name="twitter:description" content="New treatment protocols showing promise.">
    <meta name="twitter:image" content="/images/twitter-card.jpg">
    <link rel="canonical" href="/research/cachexia-update">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "MedicalScholarlyArticle",
      "headline": "Cancer Cachexia Treatment Advances",
      "author": {
        "@type": "Person",
        "name": "Dr. Jane Smith"
      },
      "datePublished": "2024-01-15"
    }
    </script>
    <script type="application/ld+json">
    This is malformed JSON that should be captured as string
    </script>
</head>
<body>
    <header>
        <h1>Cancer Cachexia Research Update</h1>
        <p>Published by Dr. Jane Smith on January 15, 2024</p>
    </header>

    <main>
        <h2>Introduction</h2>
        <p>Cancer cachexia affects a significant proportion of cancer patients, leading to muscle wasting and reduced quality of life.</p>

        <h2>Key Findings</h2>
        <p>Our recent study demonstrates promising results with novel therapeutic interventions.</p>

        <h3>Treatment Protocols</h3>
        <p>The new protocols show improved patient outcomes across multiple cancer types.</p>

        <h2>References</h2>
        <ul>
            <li><a href="/studies/study-1">Previous Study on Cachexia</a></li>
            <li><a href="https://example.com/external">External Reference</a></li>
            <li><a href="mailto:info@example.com">Contact Us</a></li>
            <li><a href="javascript:void(0)">JavaScript Link</a></li>
        </ul>

        <h2>Images</h2>
        <img src="/images/graph1.png" alt="Patient outcome graph">
        <img src="https://cdn.example.com/chart.jpg" alt="Treatment timeline">
        <img src="relative/path/image.png" alt="Research methodology">
    </main>

    <footer>
        <p>&copy; 2024 Medical Research Portal</p>
    </footer>

    <script>
    // This script should be removed during extraction
    console.log('Analytics');
    </script>
</body>
</html>
"""

SIMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Simple Page</title>
</head>
<body>
    <h1>Welcome</h1>
    <p>This is a simple page with minimal metadata.</p>
    <p>Second paragraph for testing paragraph preservation.</p>
</body>
</html>
"""

BROKEN_HTML = """
<html>
<head>
    <title>Broken Markup Test
<body>
    <h1>Missing closing tags
    <p>This HTML has broken markup
    <div>Unclosed div
    <p>But should still extract text
    <a href="/link">Link without closing tag
</html>
"""


# ============================================================================
# Test Cases
# ============================================================================

def test_complex_html_extraction():
    """Test extraction from complex HTML with full metadata."""
    base_url = "https://example.com"
    url = "https://example.com/research/cachexia-update"

    result = extract_text_and_metadata(
        COMPLEX_HTML,
        base_url=base_url,
        url_for_context=url,
        max_links=50,
        max_images=50
    )

    # Test text extraction
    assert result.text, "Text should not be empty"
    assert "Cancer Cachexia Research Update" in result.text
    assert "promising results" in result.text
    # Check paragraph preservation (double newlines)
    assert "\n\n" in result.text, "Should have paragraph boundaries"

    # Test metadata: basic fields
    assert result.metadata.title == "Cancer Cachexia Research Update"
    assert "Latest findings" in result.metadata.description
    assert result.metadata.canonical_url == "https://example.com/research/cachexia-update"
    assert result.metadata.lang == "en"
    assert result.metadata.charset == "UTF-8"
    assert result.metadata.url == url
    assert result.metadata.base_url == base_url

    # Test authors
    assert len(result.metadata.authors) > 0
    assert "Dr. Jane Smith" in result.metadata.authors

    # Test dates (should be ISO 8601 if dateparser available, or original format)
    assert result.metadata.publish_date is not None
    assert result.metadata.modified_date is not None

    # Test keywords
    assert len(result.metadata.keywords) > 0
    assert "cancer" in result.metadata.keywords
    assert "cachexia" in result.metadata.keywords

    # Test OpenGraph
    assert result.metadata.og.title == "Cancer Cachexia Research Update"
    assert "Breakthrough findings" in result.metadata.og.description
    assert result.metadata.og.type == "article"
    assert result.metadata.og.site_name == "Medical Research Portal"
    assert result.metadata.og.image == "https://example.com/images/research-hero.jpg"
    assert result.metadata.og.url == "https://example.com/research/cachexia"

    # Test Twitter Card
    assert result.metadata.twitter.card == "summary_large_image"
    assert result.metadata.twitter.title == "Cancer Cachexia Research"
    assert "treatment protocols" in result.metadata.twitter.description
    assert result.metadata.twitter.image == "https://example.com/images/twitter-card.jpg"

    # Test headings
    assert "h1" in result.metadata.headings
    assert "Cancer Cachexia Research Update" in result.metadata.headings["h1"]
    assert "h2" in result.metadata.headings
    assert "Introduction" in result.metadata.headings["h2"]
    assert "h3" in result.metadata.headings
    assert "Treatment Protocols" in result.metadata.headings["h3"]

    # Test links
    assert len(result.metadata.top_links) > 0
    assert len(result.metadata.top_links) <= 50, "Should respect max_links limit"

    # Check absolutized links
    for link in result.metadata.top_links:
        assert link.href, "Link href should not be empty"
        # Should not include mailto, javascript, data
        assert not link.href.lower().startswith(('mailto:', 'javascript:', 'data:'))
        # Internal links should be absolutized
        if not link.href.startswith('http'):
            assert False, f"Link should be absolute: {link.href}"

    # Check specific links exist
    link_hrefs = [l.href for l in result.metadata.top_links]
    assert "https://example.com/studies/study-1" in link_hrefs
    assert "https://example.com/external" in link_hrefs
    # mailto and javascript should be excluded
    assert not any('mailto:' in h for h in link_hrefs)
    assert not any('javascript:' in h for h in link_hrefs)

    # Test images
    assert len(result.metadata.top_images) > 0
    assert len(result.metadata.top_images) <= 50, "Should respect max_images limit"

    # Check absolutized images
    for image in result.metadata.top_images:
        assert image.src, "Image src should not be empty"
        # Should be absolutized
        assert image.src.startswith('http'), f"Image should be absolute: {image.src}"

    # Check specific images
    image_srcs = [img.src for img in result.metadata.top_images]
    assert "https://example.com/images/graph1.png" in image_srcs
    assert "https://cdn.example.com/chart.jpg" in image_srcs
    assert "https://example.com/relative/path/image.png" in image_srcs

    # Check image alt texts
    image_alts = [img.alt for img in result.metadata.top_images if img.alt]
    assert "Patient outcome graph" in image_alts

    # Test JSON-LD
    assert len(result.metadata.json_ld) > 0
    assert len(result.metadata.json_ld) <= 3, "Should limit to 3 JSON-LD blocks"

    # First block should be parsed as dict
    first_block = result.metadata.json_ld[0]
    if isinstance(first_block, dict):
        assert first_block.get("@type") == "MedicalScholarlyArticle"
        assert "Cancer Cachexia" in first_block.get("headline", "")

    # Second block (malformed) should be captured as string
    if len(result.metadata.json_ld) > 1:
        second_block = result.metadata.json_ld[1]
        if isinstance(second_block, str):
            assert "malformed" in second_block.lower()

    # Test stats
    assert result.stats.word_count > 0, "Should have word count"
    assert result.stats.char_count > 0, "Should have character count"
    assert result.stats.paragraph_count >= 1, "Should have at least 1 paragraph"
    assert result.stats.link_count == len(result.metadata.top_links)
    assert result.stats.image_count == len(result.metadata.top_images)

    # Verify word count is reasonable
    assert result.stats.word_count > 20, "Should have substantial word count"


def test_simple_html_extraction():
    """Test extraction from simple HTML with minimal metadata."""
    result = extract_text_and_metadata(SIMPLE_HTML)

    # Basic assertions
    assert result.text, "Text should not be empty"
    assert "Welcome" in result.text
    assert "simple page" in result.text
    assert "Second paragraph" in result.text

    # Check paragraph preservation
    assert "\n\n" in result.text, "Should preserve paragraph boundaries"

    # Metadata
    assert result.metadata.title == "Simple Page"
    assert result.metadata.description is None  # No description meta tag

    # Stats
    assert result.stats.word_count > 0
    assert result.stats.paragraph_count >= 2  # Two paragraphs in content


def test_broken_html_resilience():
    """Test that extractor handles broken markup gracefully without raising."""
    # Should not raise exception
    result = extract_text_and_metadata(BROKEN_HTML, base_url="https://example.com")

    # Should still extract some text
    assert result.text, "Should extract text even from broken HTML"
    assert "Broken Markup Test" in result.text or "Missing closing tags" in result.text

    # Should have basic metadata
    assert result.metadata is not None
    assert isinstance(result.stats.word_count, int)
    assert result.stats.word_count >= 0


def test_empty_html():
    """Test extraction from empty/minimal HTML."""
    empty = "<html><body></body></html>"
    result = extract_text_and_metadata(empty)

    assert result.text == "", "Empty HTML should yield empty text"
    assert result.stats.word_count == 0
    assert result.stats.paragraph_count == 0


def test_absolutize_links_without_base_url():
    """Test that links remain relative when no base_url provided."""
    html = '<html><body><a href="/relative">Link</a></body></html>'
    result = extract_text_and_metadata(html)

    assert len(result.metadata.top_links) > 0
    # Without base_url, links remain as-is
    assert result.metadata.top_links[0].href == "/relative"


def test_link_and_image_limits():
    """Test that max_links and max_images parameters work."""
    html = """
    <html><body>
    <a href="/link1">1</a>
    <a href="/link2">2</a>
    <a href="/link3">3</a>
    <a href="/link4">4</a>
    <a href="/link5">5</a>
    <img src="/img1.jpg"><img src="/img2.jpg"><img src="/img3.jpg">
    </body></html>
    """

    result = extract_text_and_metadata(html, max_links=2, max_images=1)

    assert len(result.metadata.top_links) == 2, "Should limit links to max_links"
    assert len(result.metadata.top_images) == 1, "Should limit images to max_images"


def test_script_and_style_removal():
    """Test that scripts and styles are removed from text."""
    html = """
    <html><body>
    <p>Visible text</p>
    <script>alert('Should not appear')</script>
    <style>.hidden { display: none; }</style>
    <p>More visible text</p>
    </body></html>
    """

    result = extract_text_and_metadata(html)

    assert "Visible text" in result.text
    assert "More visible text" in result.text
    assert "alert" not in result.text, "Script content should be removed"
    assert "display: none" not in result.text, "Style content should be removed"


def test_whitespace_normalization():
    """Test that whitespace is normalized correctly."""
    html = """
    <html><body>
    <p>Text   with    multiple     spaces</p>
    <p>Line one
    Line two</p>
    </body></html>
    """

    result = extract_text_and_metadata(html)

    # Multiple spaces should be collapsed to single space
    assert "multiple     spaces" not in result.text
    assert "multiple spaces" in result.text or "Text with multiple spaces" in result.text


def test_date_extraction():
    """Test date extraction from various metadata sources."""
    html = """
    <html>
    <head>
        <meta property="article:published_time" content="2024-01-15T10:30:00Z">
        <meta property="article:modified_time" content="2024-01-20T14:45:00Z">
    </head>
    <body><p>Content</p></body>
    </html>
    """

    result = extract_text_and_metadata(html)

    # Dates should be extracted (ISO format if dateparser available)
    assert result.metadata.publish_date is not None
    assert result.metadata.modified_date is not None
    # Should contain '2024' in the date string
    assert "2024" in result.metadata.publish_date
    assert "2024" in result.metadata.modified_date


if __name__ == '__main__':
    # Run tests
    import pytest
    pytest.main([__file__, '-v'])
