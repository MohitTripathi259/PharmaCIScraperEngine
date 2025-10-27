"""
Demo script for Change Analysis module.

Shows how to use the analyze_change function with sample data.
"""

import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from change_analysis import analyze_change


def create_sample_screenshot(version: int) -> bytes:
    """Create a sample screenshot image."""
    img = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, 400, 50], fill="darkblue")
    draw.text((20, 15), "Clinical Trial Portal", fill="white")

    # Content area
    draw.rectangle([20, 70, 380, 280], outline="gray", width=2)

    # Version-specific content
    if version == 1:
        draw.text((40, 90), f"Trial Status: Phase {version}", fill="black")
        draw.text((40, 120), "Participants: 100", fill="black")
        draw.text((40, 150), "Status: Pending Review", fill="orange")
        draw.rectangle([40, 180, 180, 210], fill="lightgray")
        draw.text((50, 190), "Submit", fill="black")
    else:
        draw.text((40, 90), f"Trial Status: Phase {version}", fill="black")
        draw.text((40, 120), "Participants: 150", fill="black")
        draw.text((40, 150), "Status: APPROVED", fill="green")
        draw.rectangle([40, 180, 180, 210], fill="green")
        draw.text((50, 190), "View Results", fill="white")

    # Convert to bytes
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def main():
    """Run demo analysis."""
    print("=" * 70)
    print("Change Analysis Demo")
    print("=" * 70)
    print()

    # Create sample data
    print("Creating sample screenshots...")
    prev_screenshot = create_sample_screenshot(version=1)
    cur_screenshot = create_sample_screenshot(version=2)

    prev_dom = """
    <html>
        <head><title>Clinical Trial Portal</title></head>
        <body>
            <header>
                <h1>Clinical Trial Portal</h1>
            </header>
            <main>
                <div class="trial-info">
                    <h2>Trial Status: Phase 1</h2>
                    <p>Participants: 100</p>
                    <p class="status pending">Status: Pending Review</p>
                    <button class="btn-submit">Submit</button>
                </div>
            </main>
        </body>
    </html>
    """

    cur_dom = """
    <html>
        <head><title>Clinical Trial Portal</title></head>
        <body>
            <header>
                <h1>Clinical Trial Portal</h1>
            </header>
            <main>
                <div class="trial-info">
                    <h2>Trial Status: Phase 2</h2>
                    <p>Participants: 150</p>
                    <p class="status approved">Status: APPROVED</p>
                    <button class="btn-view">View Results</button>
                </div>
            </main>
        </body>
    </html>
    """

    print("Analyzing changes...")
    print()

    # Run analysis
    result = analyze_change(
        prev_dom=prev_dom,
        cur_dom=cur_dom,
        prev_ss=prev_screenshot,
        cur_ss=cur_screenshot,
        goal="Monitor clinical trial status changes",
        domain="regulatory",
        url="https://example.com/trials/123",
        keywords=["approved", "pending", "phase", "participants"]
    )

    # Display results
    print("RESULTS:")
    print("-" * 70)
    print(f"Change Detected:     {result.has_change}")
    print(f"Text Added:          {result.text_added} lines")
    print(f"Text Removed:        {result.text_removed} lines")
    print(f"Similarity:          {result.similarity:.2%} (text + visual combined)")
    print(f"Total Diff Lines:    {result.total_diff_lines}")
    print()
    print(f"Importance:          {result.importance.upper()}")
    print(f"Importance Score:    {result.import_score:.2f}/10")
    print(f"Alert Level:         {result.alert_criteria.upper()}")
    print()
    print("Summary:")
    print(f"  {result.summary_change}")
    print()
    print("=" * 70)

    # Show how to use the result
    print()
    print("USAGE EXAMPLE:")
    print("-" * 70)
    print("# Check if action is needed")
    print(f"if result.alert_criteria == 'crit':")
    print(f"    send_alert(result.summary_change)")
    print(f"elif result.has_change:")
    print(f"    log_change(result)")
    print()

    # Show result as dict
    print("JSON OUTPUT:")
    print("-" * 70)
    import json
    print(json.dumps(result.model_dump(), indent=2))
    print()

    print("=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
