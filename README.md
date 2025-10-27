# Change Diff & Importance Analysis

Production-ready Python 3.11+ module for detecting and analyzing web page changes with intelligent importance scoring.

## Features

- **Visual Similarity Analysis**: Pure-PIL perceptual hashing (aHash/dHash) without numpy/scikit-image
- **Text Diff Analysis**: Robust DOM parsing with lxml/BeautifulSoup and difflib-based comparison
- **LLM-Powered Summarization**: Optional AWS Bedrock integration with deterministic fallback
- **Importance Scoring**: Domain-weighted scoring with keyword detection (0-10 scale)
- **Type-Safe**: Full Pydantic v2 validation with strict schemas
- **Production-Ready**: Comprehensive logging, error handling, and fast unit tests (<2s)

## Installation

```bash
# Install core dependencies
pip install -r requirements.txt

# Optional: For AWS Bedrock LLM support
pip install boto3
```

## Quick Start

### Python API

```python
from change_analysis import analyze_change

result = analyze_change(
    prev_dom="<html><body><p>Version 1</p></body></html>",
    cur_dom="<html><body><p>Version 2</p></body></html>",
    prev_ss=b"...",  # bytes, base64 data URI, or file path
    cur_ss=b"...",
    goal="Monitor regulatory changes",
    domain="regulatory",
    url="https://example.com/regulations",
    keywords=["compliance", "required", "mandatory"]
)

print(f"Change detected: {result.has_change}")
print(f"Importance: {result.importance} (score: {result.import_score}/10)")
print(f"Summary: {result.summary_change}")
print(f"Alert level: {result.alert_criteria}")
```

### HTTP API

```bash
# Start the server
uvicorn src.api.main:app --reload

# Or directly
python -m src.api.main
```

```bash
# Test the endpoint
curl -X POST http://localhost:8000/v1/changes/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "prev_dom": "<html><body><p>Old</p></body></html>",
    "cur_dom": "<html><body><p>New</p></body></html>",
    "prev_ss": "path/to/prev.png",
    "cur_ss": "path/to/cur.png",
    "goal": "Monitor changes",
    "domain": "general",
    "url": "https://example.com",
    "keywords": ["important"]
  }'
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Enable/disable LLM (default: false for deterministic behavior)
USE_BEDROCK=false

# AWS Bedrock model (if enabled)
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
```

## Result Schema

The `ChangeResult` model includes:

```python
{
    "has_change": bool,           # Whether significant change detected
    "text_added": int,            # Number of text lines/items added
    "text_removed": int,          # Number of text lines/items removed
    "similarity": float,          # Overall similarity 0-1 (1=identical)
    "total_diff_lines": int,      # Total diff lines
    "summary_change": str,        # Natural language summary
    "importance": str,            # "low" | "medium" | "critical"
    "import_score": float,        # Importance score 0-10
    "alert_criteria": str         # "low" | "med" | "crit"
}
```

## Importance Scoring

### Base Score
- Calculated from text dissimilarity (60%) + visual dissimilarity (40%)

### Domain Weights
- `regulatory`: 1.2x
- `safety`: 1.15x
- `pricing`: 1.1x
- `legal`: 1.15x
- `compliance`: 1.2x
- `security`: 1.15x
- Default: 1.0x

### Keyword Boost
- +0.2 bonus (capped) if monitored keywords appear in changes or summary

### Severity Labels
- **0.0-4.4**: `low`
- **4.5-7.4**: `medium`
- **7.5-10.0**: `critical`

## Testing

```bash
# Run all tests
pytest tests/unit/test_change_analysis.py -v

# Run with coverage
pytest tests/unit/test_change_analysis.py --cov=src/change_analysis -v
```

Tests are deterministic (USE_BEDROCK=false) and complete in <2 seconds.

## Architecture

```
src/
├── change_analysis/
│   ├── __init__.py           # Package exports
│   ├── schemas.py            # Pydantic models
│   ├── utils_image.py        # Pure-PIL perceptual hashing
│   ├── utils_dom.py          # DOM parsing & text diff
│   ├── importance.py         # Scoring logic
│   ├── llm_adapter.py        # Bedrock integration
│   └── pipeline.py           # Main analyze_change()
└── api/
    ├── main.py               # FastAPI app
    └── routes_change.py      # API endpoints

tests/
└── unit/
    └── test_change_analysis.py  # Comprehensive unit tests
```

## Screenshots

Screenshots can be provided as:
1. **Raw bytes**: `prev_ss=image_bytes`
2. **Base64 data URI**: `prev_ss="data:image/png;base64,iVBORw0K..."`
3. **File path**: `prev_ss="screenshots/prev.png"`

All paths use `pathlib` for Windows compatibility.

## LLM Integration

When `USE_BEDROCK=true`:
- Calls AWS Bedrock with Claude 3.5 Sonnet
- Generates detailed change summaries with salient points
- Identifies keyword matches automatically
- Gracefully falls back to local summarizer on errors

When disabled or unavailable:
- Uses deterministic local summarizer
- Still provides meaningful summaries based on heuristics
- No external dependencies or API calls

## API Endpoints

- `POST /v1/changes/analyze` - Analyze a change
- `GET /v1/changes/health` - Service health check
- `GET /health` - Global health check
- `GET /` - API info
- `GET /docs` - Interactive API documentation (Swagger UI)

## License

Proprietary - Internal use only

## Support

For issues or questions, contact the platform engineering team.
