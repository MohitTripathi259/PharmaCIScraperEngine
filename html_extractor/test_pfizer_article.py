"""
QA Test: Real-world Pfizer article extraction validation.

Tests the HTML extractor with a complex real-world Pfizer press release.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from change_analysis.html_extractor import extract_text_and_metadata


def validate_extraction():
    """Perform comprehensive validation of Pfizer article extraction."""

    print("="*80)
    print("HTML EXTRACTOR QA TEST - Real Pfizer Article")
    print("="*80)
    print()

    # Load HTML
    print("[1/5] Loading Pfizer article HTML...")
    html_file = Path("pfizer_ponsegromab_article.html")
    html = html_file.read_text(encoding='utf-8')
    print(f"  HTML size: {len(html)} characters")
    print()

    # Extract
    print("[2/5] Extracting text and metadata...")
    url = "https://www.pfizer.com/news/press-release/press-release-detail/pfizer-presents-positive-data-phase-2-study-ponsegromab"
    base_url = "https://www.pfizer.com"

    try:
        result = extract_text_and_metadata(
            html_content=html,
            base_url=base_url,
            url_for_context=url,
            max_links=50,
            max_images=50
        )
        print("  Extraction completed successfully!")
        print()
    except Exception as e:
        print(f"  [FAIL] Extraction failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Validation tracking
    issues = []
    checks_passed = 0
    checks_total = 0

    # Validate text
    print("[3/5] Validating extracted text...")
    checks_total += 1
    if result.text and len(result.text) > 0:
        print(f"  [PASS] Text extracted: {len(result.text)} characters")
        checks_passed += 1
    else:
        print("  [FAIL] Text is empty")
        issues.append("Text extraction returned empty string")

    # Check for script/style in text
    checks_total += 1
    if '<script' in result.text.lower() or '<style' in result.text.lower():
        print("  [FAIL] Script or style tags found in extracted text")
        issues.append("Script/style tags not properly removed")
    else:
        print("  [PASS] No script/style tags in text")
        checks_passed += 1

    # Check paragraph preservation
    checks_total += 1
    if '\n\n' in result.text:
        print("  [PASS] Paragraph boundaries preserved (double newlines found)")
        checks_passed += 1
    else:
        print("  [WARN] No paragraph boundaries found")

    print()

    # Validate metadata
    print("[4/5] Validating metadata...")

    # Title
    checks_total += 1
    if result.metadata.title:
        print(f"  [PASS] Title: {result.metadata.title[:80]}...")
        checks_passed += 1
        if "ponsegromab" in result.metadata.title.lower() or "pfizer" in result.metadata.title.lower():
            print("         [INFO] Title contains expected keywords")
    else:
        print("  [FAIL] Title is missing")
        issues.append("Title not extracted")

    # Description
    checks_total += 1
    if result.metadata.description:
        print(f"  [PASS] Description: {result.metadata.description[:80]}...")
        checks_passed += 1
    else:
        print("  [INFO] Description not present (may be optional)")

    # Publish date
    checks_total += 1
    if result.metadata.publish_date:
        print(f"  [PASS] Publish date: {result.metadata.publish_date}")
        checks_passed += 1
    else:
        print("  [WARN] Publish date not found (check if article has date metadata)")

    # Headings
    checks_total += 1
    if result.metadata.headings and "h1" in result.metadata.headings:
        h1_list = result.metadata.headings["h1"]
        print(f"  [PASS] H1 headings found: {len(h1_list)}")
        if h1_list:
            print(f"         First H1: {h1_list[0][:80]}...")
        checks_passed += 1
    else:
        print("  [FAIL] No H1 headings found")
        issues.append("H1 headings not extracted")

    # Links
    checks_total += 1
    if len(result.metadata.top_links) > 0:
        print(f"  [PASS] Links found: {len(result.metadata.top_links)}")

        # Check all links are absolute
        relative_links = []
        invalid_schemes = []
        for link in result.metadata.top_links:
            if not link.href.startswith('http'):
                relative_links.append(link.href)
            if link.href.lower().startswith(('mailto:', 'javascript:', 'data:')):
                invalid_schemes.append(link.href)

        checks_total += 1
        if relative_links:
            print(f"  [FAIL] Found {len(relative_links)} relative links:")
            for rl in relative_links[:3]:
                print(f"         - {rl}")
            issues.append(f"Relative links not absolutized: {len(relative_links)} found")
        else:
            print("  [PASS] All links are absolute")
            checks_passed += 1

        checks_total += 1
        if invalid_schemes:
            print(f"  [FAIL] Found {len(invalid_schemes)} invalid scheme links (mailto/javascript/data)")
            issues.append(f"Invalid schemes not filtered: {len(invalid_schemes)} found")
        else:
            print("  [PASS] No invalid scheme links")
            checks_passed += 1

        # Show sample links
        print("         Sample links:")
        for link in result.metadata.top_links[:3]:
            print(f"         - {link.href[:80]}... ({link.text[:40] if link.text else 'no text'}...)")

        checks_passed += 1
    else:
        print("  [WARN] No links found (unusual for press release)")

    # Images
    checks_total += 1
    if len(result.metadata.top_images) > 0:
        print(f"  [PASS] Images found: {len(result.metadata.top_images)}")

        # Check all images are absolute
        relative_images = []
        for img in result.metadata.top_images:
            if not img.src.startswith('http'):
                relative_images.append(img.src)

        checks_total += 1
        if relative_images:
            print(f"  [FAIL] Found {len(relative_images)} relative image URLs:")
            for ri in relative_images[:3]:
                print(f"         - {ri}")
            issues.append(f"Relative image URLs not absolutized: {len(relative_images)} found")
        else:
            print("  [PASS] All image URLs are absolute")
            checks_passed += 1

        # Show sample images
        print("         Sample images:")
        for img in result.metadata.top_images[:3]:
            print(f"         - {img.src[:80]}... (alt: {img.alt[:40] if img.alt else 'none'}...)")

        checks_passed += 1
    else:
        print("  [INFO] No images found")

    # JSON-LD
    checks_total += 1
    if result.metadata.json_ld:
        print(f"  [PASS] JSON-LD blocks found: {len(result.metadata.json_ld)}")
        for i, block in enumerate(result.metadata.json_ld):
            if isinstance(block, dict):
                print(f"         Block {i+1}: Parsed dict with {len(block)} keys")
            else:
                print(f"         Block {i+1}: Raw string ({len(str(block))} chars)")
        checks_passed += 1
    else:
        print("  [INFO] No JSON-LD blocks found")

    # OpenGraph
    if result.metadata.og.title or result.metadata.og.description:
        print(f"  [INFO] OpenGraph data found:")
        if result.metadata.og.title:
            print(f"         og:title: {result.metadata.og.title[:60]}...")
        if result.metadata.og.description:
            print(f"         og:description: {result.metadata.og.description[:60]}...")

    print()

    # Validate stats
    print("[5/5] Validating statistics...")

    checks_total += 1
    if result.stats.word_count > 0:
        print(f"  [PASS] Word count: {result.stats.word_count}")
        checks_passed += 1
    else:
        print("  [FAIL] Word count is 0")
        issues.append("Word count calculation failed")

    checks_total += 1
    if result.stats.char_count > 0:
        print(f"  [PASS] Character count: {result.stats.char_count}")
        checks_passed += 1
    else:
        print("  [FAIL] Character count is 0")
        issues.append("Character count calculation failed")

    checks_total += 1
    if result.stats.paragraph_count > 0:
        print(f"  [PASS] Paragraph count: {result.stats.paragraph_count}")
        checks_passed += 1
    else:
        print("  [WARN] Paragraph count is 0")

    checks_total += 1
    if result.stats.link_count == len(result.metadata.top_links):
        print(f"  [PASS] Link count matches: {result.stats.link_count}")
        checks_passed += 1
    else:
        print(f"  [FAIL] Link count mismatch: stats={result.stats.link_count}, actual={len(result.metadata.top_links)}")
        issues.append("Link count inconsistency")

    checks_total += 1
    if result.stats.image_count == len(result.metadata.top_images):
        print(f"  [PASS] Image count matches: {result.stats.image_count}")
        checks_passed += 1
    else:
        print(f"  [FAIL] Image count mismatch: stats={result.stats.image_count}, actual={len(result.metadata.top_images)}")
        issues.append("Image count inconsistency")

    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()

    # Generate markdown table
    print("## Extraction Results\n")
    print("| Field | Value |")
    print("|-------|-------|")
    print(f"| **title** | {result.metadata.title or 'N/A'} |")
    print(f"| **description** | {result.metadata.description[:100] if result.metadata.description else 'N/A'}... |")
    print(f"| **publish_date** | {result.metadata.publish_date or 'N/A'} |")
    print(f"| **word_count** | {result.stats.word_count} |")
    print(f"| **char_count** | {result.stats.char_count} |")
    print(f"| **paragraph_count** | {result.stats.paragraph_count} |")
    print(f"| **link_count** | {result.stats.link_count} |")
    print(f"| **image_count** | {result.stats.image_count} |")
    first_h1 = result.metadata.headings.get("h1", ["N/A"])[0] if result.metadata.headings.get("h1") else "N/A"
    print(f"| **first_heading** | {first_h1[:80]}... |")
    print(f"| **number_of_json_ld_blocks** | {len(result.metadata.json_ld)} |")
    print(f"| **canonical_url** | {result.metadata.canonical_url or 'N/A'} |")
    print(f"| **language** | {result.metadata.lang or 'N/A'} |")
    print(f"| **checks_passed** | {checks_passed}/{checks_total} |")

    # Verdict
    print()
    print("## Verdict\n")

    if len(issues) == 0 and checks_passed >= checks_total * 0.9:
        print("**Status**: [PASS] Extractor works fine on real complex page")
        print()
        print("The HTML extractor successfully processed the Pfizer press release with:")
        print(f"- {checks_passed}/{checks_total} checks passed")
        print("- All critical fields extracted correctly")
        print("- Links and images properly absolutized")
        print("- No script/style content in extracted text")
        print("- Robust handling of complex real-world HTML")
        verdict = "PASS"
    else:
        print(f"**Status**: [FAIL] Extractor needs fixes ({len(issues)} issues found)")
        print()
        print("**Issues identified:**")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        print()
        print(f"**Checks passed**: {checks_passed}/{checks_total}")
        verdict = "FAIL"

    print()
    print("="*80)

    # Save detailed results
    output_file = Path("pfizer_extraction_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")

    return verdict == "PASS"


if __name__ == '__main__':
    success = validate_extraction()
    sys.exit(0 if success else 1)
