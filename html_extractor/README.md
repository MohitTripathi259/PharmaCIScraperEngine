# HTML Extractor - Production-Ready HTML to Text + Metadata

A robust, production-ready Python module for extracting normalized text and rich metadata from HTML content.

## Features

- **Normalized Text Extraction**: Paragraph-preserving, whitespace-normalized visible text
- **Rich Metadata**: Title, description, canonical URL, authors, dates, keywords
- **Social Media Tags**: Full OpenGraph and Twitter Card extraction
- **Structured Data**: JSON-LD schema.org data collection
- **Link & Image Collection**: Absolutized URLs with customizable limits
- **Heading Extraction**: All H1-H6 headings with text content
- **Robust Parsing**: Never fails on malformed HTML
- **Fast Performance**: < 150ms typical for article-sized pages
- **FastAPI Integration**: Ready-to-use API endpoint

## Installation

```bash
# From requirements.txt
pip install -r requirements.txt

# Or install as editable package
pip install -e .
```

## Quick Start

### Python API

```python
from src.change_analysis.html_extractor import extract_text_and_metadata

html = """
<html>
<head>
    <title>Article Title</title>
    <meta name="description" content="Article description">
</head>
<body>
    <h1>Main Heading</h1>
    <p>Article content goes here.</p>
</body>
</html>
"""

result = extract_text_and_metadata(
    html_content=html,
    base_url="https://example.com",
    url_for_context="https://example.com/article",
    max_links=50,
    max_images=50
)

# Access extracted data
print(f"Title: {result.metadata.title}")
print(f"Text: {result.text}")
print(f"Word Count: {result.stats.word_count}")
print(f"Links: {len(result.metadata.top_links)}")
```

### FastAPI Server

```bash
# Start server
cd html_extractor
python -m uvicorn src.api.main:app --reload --port 8080

# Access Swagger docs
# Open http://localhost:8080/docs
```

#### API Request Example

```bash
curl -X POST "http://localhost:8080/v1/extract/html" \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<html><body><h1>Test</h1><p>Content</p></body></html>",
    "base_url": "https://example.com",
    "url": "https://example.com/page",
    "max_links": 50,
    "max_images": 50
  }'
```

## Output Structure

### HtmlExtractionResult

```python
{
    "text": str,              # Normalized, paragraph-preserving text
    "metadata": {
        "url": str,
        "base_url": str,
        "title": str,
        "description": str,
        "canonical_url": str,
        "lang": str,
        "charset": str,
        "authors": List[str],
        "publish_date": str,  # ISO 8601
        "modified_date": str, # ISO 8601
        "keywords": List[str],
        "og": {              # OpenGraph
            "title": str,
            "description": str,
            "type": str,
            "site_name": str,
            "image": str,
            "url": str
        },
        "twitter": {         # Twitter Card
            "card": str,
            "title": str,
            "description": str,
            "image": str
        },
        "headings": {        # h1..h6 lists
            "h1": List[str],
            "h2": List[str],
            ...
        },
        "top_links": [       # LinkItem[]
            {"href": str, "text": str}
        ],
        "top_images": [      # ImageItem[]
            {"src": str, "alt": str}
        ],
        "json_ld": List[Dict | str]  # Up to 3 blocks
    },
    "stats": {
        "word_count": int,
        "char_count": int,
        "paragraph_count": int,
        "link_count": int,
        "image_count": int
    }
}
```

## Testing

```bash
# Run all tests
python -m pytest tests/unit/test_html_extractor.py -v

# Quick test
python -m pytest tests/unit/test_html_extractor.py -q

# Run specific test
python -m pytest tests/unit/test_html_extractor.py::test_complex_html_extraction -v
```

### Test Coverage

- Complex HTML with full metadata
- Simple HTML with minimal metadata
- Broken/malformed HTML resilience
- Empty HTML handling
- Link and image absolutization
- Whitespace normalization
- Script/style removal
- Date extraction
- JSON-LD parsing

## Performance

- **Typical execution**: < 150ms for article-sized pages
- **No network calls**: All processing is local
- **Memory efficient**: Minimal memory footprint
- **Deterministic**: Same input → same output

## Dependencies

- **beautifulsoup4** (>=4.11.0): HTML parsing with lxml
- **lxml** (>=4.9.0): Fast and robust XML/HTML processor
- **pydantic** (>=2.0.0): Type-safe data validation
- **fastapi** (>=0.100.0): Modern API framework
- **uvicorn** (>=0.20.0): ASGI server
- **dateparser** (>=1.1.0): Flexible date parsing

## Architecture

```
html_extractor/
├── src/
│   ├── change_analysis/
│   │   └── html_extractor.py    # Core extraction logic
│   └── api/
│       ├── main.py               # FastAPI app
│       └── routes_extract.py     # Extraction endpoint
├── tests/
│   └── unit/
│       └── test_html_extractor.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Key Features

### 1. Robust HTML Parsing

- Uses BeautifulSoup with lxml parser
- Handles malformed/broken HTML gracefully
- Never raises exceptions on parsing errors
- Removes scripts, styles, comments

### 2. Text Normalization

- Preserves paragraph boundaries (double newlines)
- Collapses internal whitespace
- Unescapes HTML entities
- Removes non-visible content

### 3. URL Absolutization

- Converts relative URLs to absolute using base_url
- Rejects `javascript:`, `data:`, `mailto:` schemes
- Validates URL structure
- Handles edge cases safely

### 4. Date Parsing

- Supports multiple metadata sources:
  - `article:published_time` (OpenGraph)
  - `article:modified_time` (OpenGraph)
  - `<meta name="date">`
  - `itemprop="datePublished"`
- Uses dateparser for flexible parsing
- Returns ISO 8601 format

### 5. JSON-LD Extraction

- Collects up to 3 structured data blocks
- Limits each block to 10 KB
- Parses valid JSON to dict
- Captures malformed JSON as string

## Configuration

### max_links & max_images

Limit the number of links/images collected to prevent large payloads:

```python
result = extract_text_and_metadata(
    html,
    max_links=100,   # Default: 50
    max_images=100   # Default: 50
)
```

### URL Parameters

- **base_url**: Used for absolutizing relative links/images
- **url_for_context**: The page URL for metadata context

## Error Handling

The extractor is designed to never fail:

- Malformed HTML → best-effort extraction
- Missing metadata → None or empty lists
- Invalid URLs → original URL returned
- Parse errors → minimal valid result returned

## Production Readiness

✅ **Type Safety**: Full Pydantic v2 typing
✅ **Windows Compatible**: pathlib-based paths
✅ **No Network Calls**: All processing is local
✅ **Performance**: Optimized for speed
✅ **Tested**: Comprehensive unit tests
✅ **Documented**: Rich docstrings and examples
✅ **API Ready**: FastAPI integration included

## Integration Examples

### With Web Scraper

```python
import requests
from src.change_analysis.html_extractor import extract_text_and_metadata

# Fetch HTML
response = requests.get('https://example.com/article')
html = response.text

# Extract
result = extract_text_and_metadata(
    html,
    base_url='https://example.com',
    url_for_context=response.url
)

# Use extracted data
print(f"Title: {result.metadata.title}")
print(f"Summary: {result.text[:200]}...")
```

### With File Storage

```python
from pathlib import Path

# Read from file
html_file = Path('article.html')
html = html_file.read_text(encoding='utf-8')

# Extract
result = extract_text_and_metadata(html)

# Save results
import json
output = Path('extracted.json')
output.write_text(json.dumps(result.model_dump(), indent=2))
```

## Support

For issues or questions:
1. Check the test cases in `tests/unit/test_html_extractor.py` for examples
2. Review docstrings in `src/change_analysis/html_extractor.py`
3. Test with `/docs` endpoint when API is running

## License

MIT License - see project root for details

---

**Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: 2025-10-27
