"""
Demo batch processing script for change analysis.

Shows how to process multiple pages in a loop with different domains.
"""
from src.change_analysis.pipeline import analyze_change

pages = [
    ("<h1>Trial 3</h1>", "<h1>Trial 4</h1>", "", "", "Track trials", "regulatory", "https://example.com/p1"),
    ("<p>Price $15</p>", "<p>Price $19</p>", "", "", "Monitor pricing", "pricing", "https://example.com/p2"),
    ("<p>Safety v1.0</p>", "<p>Safety v1.1</p>", "", "", "Check safety labels", "safety", "https://example.com/p3")
]

print("=" * 80)
print("Batch Change Analysis Demo")
print("=" * 80)
print()

for prev, cur, pimg, cimg, goal, dom, url in pages:
    res = analyze_change(prev, cur, pimg, cimg, goal, dom, url)
    print(f"URL:        {url}")
    print(f"Domain:     {dom}")
    print(f"Importance: {res.importance} ({res.import_score}/10)")
    print(f"Alert:      {res.alert_criteria}")
    print(f"Summary:    {res.summary_change}")
    print("-" * 80)
