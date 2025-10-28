"""
Depth-based link extraction demo.

Demonstrates extracting content recursively:
- Depth 0: Original page
- Depth 1: Extract content from top N links in original page
- Depth 2: Extract content from top N links in each depth 1 page
"""

import sys
from pathlib import Path
import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from change_analysis.html_extractor import extract_text_and_metadata


def fetch_url(url: str, timeout: int = 10) -> str:
    """Fetch HTML content from a URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='ignore')
    except (URLError, HTTPError) as e:
        print(f"  [ERROR] Failed to fetch {url}: {e}")
        return None


def extract_with_depth(
    start_url: str,
    max_depth: int = 2,
    links_per_level: int = 3,
    max_links: int = 50,
    delay: float = 1.0
):
    """
    Extract content with depth-based crawling.

    Args:
        start_url: Initial URL to start extraction
        max_depth: Maximum depth to crawl (0 = only start URL)
        links_per_level: Number of links to follow at each level
        max_links: Maximum links to extract per page
        delay: Delay between requests (seconds)
    """

    print("="*80)
    print("DEPTH-BASED CONTENT EXTRACTION DEMO")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Start URL: {start_url}")
    print(f"  Max Depth: {max_depth}")
    print(f"  Links per level: {links_per_level}")
    print(f"  Max links per page: {max_links}")
    print(f"  Delay between requests: {delay}s")
    print()

    # Track all extracted pages
    extracted_pages = []

    # Queue: (url, depth, parent_index)
    queue = [(start_url, 0, None)]
    visited = set()

    while queue:
        url, depth, parent_idx = queue.pop(0)

        # Skip if already visited or depth exceeded
        if url in visited or depth > max_depth:
            continue

        visited.add(url)

        print("-"*80)
        print(f"DEPTH {depth}: Extracting {url}")
        if parent_idx is not None:
            print(f"  (Parent: Page #{parent_idx + 1})")
        print("-"*80)

        # Fetch HTML
        html = fetch_url(url)
        if not html:
            print(f"  [SKIP] Could not fetch URL\n")
            continue

        # Extract content
        base_url = "/".join(url.split("/")[:3])  # https://domain.com
        result = extract_text_and_metadata(
            html_content=html,
            base_url=base_url,
            url_for_context=url,
            max_links=max_links,
            max_images=20
        )

        # Store result
        page_info = {
            "url": url,
            "depth": depth,
            "parent_idx": parent_idx,
            "title": result.metadata.title,
            "word_count": result.stats.word_count,
            "link_count": len(result.metadata.top_links),
            "image_count": len(result.metadata.top_images),
            "links": result.metadata.top_links,
            "text_preview": result.text[:500]
        }
        page_idx = len(extracted_pages)
        extracted_pages.append(page_info)

        # Print summary
        print(f"\n  [SUCCESS] Extraction complete!")
        print(f"  Title: {result.metadata.title[:60]}...")
        print(f"  Content: {result.stats.word_count} words, {result.stats.char_count} chars")
        print(f"  Links found: {len(result.metadata.top_links)}")
        print(f"  Images found: {len(result.metadata.top_images)}")
        print(f"\n  Text preview:")
        print(f"  {result.text[:200].replace(chr(10), ' ')}...")

        # Add top links to queue if depth allows
        if depth < max_depth and len(result.metadata.top_links) > 0:
            print(f"\n  [INFO] Adding top {links_per_level} links to queue for depth {depth + 1}:")

            # Filter out navigation/anchor links
            content_links = [
                link for link in result.metadata.top_links
                if not link.href.endswith('#')
                and '#' not in link.href.split('/')[-1]
                and link.href != base_url
                and link.href != base_url + "/"
            ]

            for i, link in enumerate(content_links[:links_per_level]):
                if link.href not in visited:
                    queue.append((link.href, depth + 1, page_idx))
                    print(f"    {i+1}. {link.text[:50] if link.text else 'No text'} -> {link.href[:60]}...")

        print()

        # Delay between requests
        if queue:  # Don't delay after last request
            time.sleep(delay)

    # Generate summary
    print("="*80)
    print("EXTRACTION SUMMARY")
    print("="*80)
    print(f"\nTotal pages extracted: {len(extracted_pages)}")
    print(f"\nPages by depth:")

    for d in range(max_depth + 1):
        pages_at_depth = [p for p in extracted_pages if p["depth"] == d]
        if pages_at_depth:
            print(f"\n  Depth {d}: {len(pages_at_depth)} pages")
            for i, page in enumerate(pages_at_depth, 1):
                print(f"    {i}. {page['title'][:50]}... ({page['word_count']} words, {page['link_count']} links)")

    # Save results
    output_file = Path("depth_extraction_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert LinkItem objects to dicts for JSON serialization
        for page in extracted_pages:
            page['links'] = [
                {"href": link.href, "text": link.text}
                for link in page['links']
            ]
        json.dump(extracted_pages, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")
    print()

    return extracted_pages


if __name__ == '__main__':
    # Test with Pfizer article
    pfizer_url = "https://www.pfizer.com/news/press-release/press-release-detail/pfizer-presents-positive-data-phase-2-study-ponsegromab"

    print("\n" + "="*80)
    print("DEMO: Depth-based extraction from Pfizer article")
    print("="*80)
    print("\nThis will:")
    print("1. Extract content from the original Pfizer article (Depth 0)")
    print("2. Extract content from top 3 links in that article (Depth 1)")
    print("3. Extract content from top 3 links in each Depth 1 page (Depth 2)")
    print("\nTotal expected extractions: 1 + 3 + (3*3) = 13 pages")
    print("="*80)
    print()

    input("Press Enter to start extraction (or Ctrl+C to cancel)...")
    print()

    results = extract_with_depth(
        start_url=pfizer_url,
        max_depth=2,
        links_per_level=3,
        max_links=50,
        delay=2.0  # 2 second delay between requests
    )

    print("="*80)
    print("DEMO COMPLETE!")
    print("="*80)
    print(f"\nExtracted {len(results)} pages across 3 depth levels")
    print("Results saved to: depth_extraction_results.json")
    print()
