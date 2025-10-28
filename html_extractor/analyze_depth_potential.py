"""
Analyze depth extraction potential from existing Pfizer extraction results.

Shows what would be extracted at each depth level without making actual web requests.
"""

import json
from pathlib import Path


def analyze_depth_potential(results_file: str, links_per_level: int = 3):
    """Analyze what would be extracted at each depth level."""

    print("="*80)
    print("DEPTH EXTRACTION ANALYSIS - PFIZER ARTICLE")
    print("="*80)
    print()

    # Load existing results
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Depth 0 - Original article
    print("DEPTH 0: Original Article")
    print("-"*80)
    print(f"URL: {data['metadata']['url']}")
    print(f"Title: {data['metadata']['title']}")
    print(f"Content: {data['stats']['word_count']} words")
    print(f"Total links found: {len(data['metadata']['top_links'])}")
    print()

    # Filter content links (skip navigation/anchors)
    all_links = data['metadata']['top_links']
    base_url = data['metadata']['base_url']

    content_links = []
    for link in all_links:
        href = link['href']
        # Skip anchors, homepage, and pure navigation links
        if (not href.endswith('#')
            and '#main-content' not in href
            and href != base_url
            and href != base_url + "/"
            and link.get('text')
            and link['text'].strip()
            and link['text'].strip() != 'No text'):
            content_links.append(link)

    print(f"Content links (filtered from {len(all_links)} total): {len(content_links)}")
    print()

    # Depth 1 - Top N links from original
    print("="*80)
    print(f"DEPTH 1: Top {links_per_level} Links from Original Article")
    print("="*80)
    print()

    depth1_links = content_links[:links_per_level]

    for i, link in enumerate(depth1_links, 1):
        print(f"{i}. {link['text'][:60]}")
        print(f"   URL: {link['href']}")
        print(f"   [Would extract content from this page]")
        print()

    # Depth 2 - Theoretical extraction
    print("="*80)
    print(f"DEPTH 2: Would Extract Top {links_per_level} Links from Each Depth 1 Page")
    print("="*80)
    print()
    print(f"Expected extractions at Depth 2: {len(depth1_links)} pages × {links_per_level} links = {len(depth1_links) * links_per_level} pages")
    print()

    # Summary
    print("="*80)
    print("EXTRACTION SUMMARY")
    print("="*80)
    print()
    print(f"Total pages that would be extracted with depth=2:")
    print(f"  Depth 0: 1 page (original)")
    print(f"  Depth 1: {len(depth1_links)} pages")
    print(f"  Depth 2: {len(depth1_links) * links_per_level} pages (estimated)")
    print(f"  ---")
    print(f"  TOTAL: {1 + len(depth1_links) + (len(depth1_links) * links_per_level)} pages")
    print()

    # Show all available content links
    print("="*80)
    print(f"ALL AVAILABLE CONTENT LINKS IN ORIGINAL ARTICLE ({len(content_links)} total)")
    print("="*80)
    print()

    for i, link in enumerate(content_links[:20], 1):  # Show first 20
        text = link['text'][:50] if link.get('text') else 'No text'
        href = link['href'][:70]
        print(f"{i:2}. {text:50} -> {href}")

    if len(content_links) > 20:
        print(f"... and {len(content_links) - 20} more links")

    print()
    print("="*80)

    return {
        "depth_0": 1,
        "depth_1": len(depth1_links),
        "depth_2_estimated": len(depth1_links) * links_per_level,
        "total_content_links": len(content_links),
        "depth_1_links": depth1_links
    }


if __name__ == '__main__':
    results_file = Path("pfizer_extraction_results.json")

    if not results_file.exists():
        print(f"[ERROR] Results file not found: {results_file}")
        print("Please run test_pfizer_article.py first to generate the results.")
        exit(1)

    analysis = analyze_depth_potential(
        results_file=str(results_file),
        links_per_level=3
    )

    print("\nNOTE:")
    print("- The above analysis shows what WOULD be extracted")
    print("- To actually perform depth-based extraction with web requests:")
    print("  Run: python demo_depth_extraction.py")
    print()
