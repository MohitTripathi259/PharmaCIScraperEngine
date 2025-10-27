# Change Analysis Module - Handoff Contract

## Date: 2025-10-27
## Module: change-analysis v1.0.0
## Owner: Mohit Tripathi (Platform Engineering)

---

## 🎯 Purpose

This module provides **change detection and importance analysis** for web page monitoring. It compares previous vs current DOM + screenshots, computes text/visual similarity, and assigns an importance score with alert level.

---

## 📦 Library Interface (Python)

### Import
```python
from src.change_analysis.pipeline import analyze_change
```

### Function Signature
```python
def analyze_change(
    prev_dom: str,              # Previous HTML DOM
    cur_dom: str,               # Current HTML DOM
    prev_ss,                    # bytes | base64 data URI | file path | "" (none)
    cur_ss,                     # bytes | base64 data URI | file path | "" (none)
    goal: str,                  # Monitoring goal description
    domain: str,                # "regulatory" | "pricing" | "safety" | "general" | ...
    url: str,                   # URL being monitored
    keywords: list[str] | None = None  # Optional keywords for importance boost
) -> ChangeResult
```

### Return Type: `ChangeResult`
```python
class ChangeResult(BaseModel):
    has_change: bool                           # Whether change detected
    text_added: int                            # Number of words added
    text_removed: int                          # Number of words removed
    similarity: float                          # Overall similarity 0-1 (1=identical)
    total_diff_lines: int                      # Total diff lines
    summary_change: str                        # Natural language summary
    importance: Literal["low","medium","critical"]  # Importance label
    import_score: float                        # Importance score 0-10
    alert_criteria: Literal["low","med","crit"]     # Alert level
```

### Example Usage
```python
from change_analysis import analyze_change

result = analyze_change(
    prev_dom="<html><body><h1>Trial 3</h1></body></html>",
    cur_dom="<html><body><h1>Trial 4</h1></body></html>",
    prev_ss="",  # Empty string for no screenshot
    cur_ss="",
    goal="Track clinical trials",
    domain="regulatory",
    url="https://example.com/trials",
    keywords=["trial", "phase", "approval"]
)

print(f"Change: {result.has_change}")
print(f"Importance: {result.importance} ({result.import_score}/10)")
print(f"Alert: {result.alert_criteria}")
print(f"Summary: {result.summary_change}")
```

---

## 🌐 HTTP API (Optional for Services)

### Endpoint
```
POST /v1/changes/analyze
Content-Type: application/json
```

### Request Body
```json
{
  "prev_dom": "<html>...</html>",
  "cur_dom": "<html>...</html>",
  "prev_ss": "",
  "cur_ss": "",
  "goal": "Monitor regulatory changes",
  "domain": "regulatory",
  "url": "https://example.com/page",
  "keywords": ["compliance", "regulation"]
}
```

### Response (200 OK)
```json
{
  "has_change": true,
  "text_added": 5,
  "text_removed": 2,
  "similarity": 0.8543,
  "total_diff_lines": 7,
  "summary_change": "Content modified on regulatory page: 5 added, 2 removed. (7 diff lines).",
  "importance": "medium",
  "import_score": 5.67,
  "alert_criteria": "med"
}
```

### Starting the API Server
```bash
# Development
uvicorn src.api.main:app --reload --port 8080

# Production
uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --workers 4
```

---

## 🔌 Integration Points

### Upstream Dependencies

#### 1. S3/DDB Fetcher (Senior Engineer)
**Responsibility:** Load previous state
- Fetches previous DOM from storage
- Retrieves previous screenshot from S3
- Provides to change analysis module

**Data Format:**
```python
{
    "prev_dom": "<html>...</html>",    # String
    "prev_ss": "s3://bucket/key"       # S3 path or bytes or base64
}
```

#### 2. Kotesh (Current State Provider)
**Responsibility:** Capture current state
- Provides current DOM after page load
- Captures current screenshot
- Passes to change analysis module

**Data Format:**
```python
{
    "cur_dom": "<html>...</html>",     # String
    "cur_ss": bytes_or_path            # Bytes or file path
}
```

#### 3. Orchestration Layer
**Responsibility:** Loop and aggregate
- Iterates over links (e.g., 3 links, depth 3)
- Calls `analyze_change()` for each page
- Aggregates results
- Applies business logic for alerting

**Example Flow:**
```python
results = []
for link in links:
    for depth in range(3):
        # Get previous state from S3/DDB
        prev_state = fetcher.load(link, depth)

        # Get current state from crawler
        cur_state = kotesh.capture(link, depth)

        # Analyze change
        result = analyze_change(
            prev_dom=prev_state['dom'],
            cur_dom=cur_state['dom'],
            prev_ss=prev_state['screenshot'],
            cur_ss=cur_state['screenshot'],
            goal=monitoring_config['goal'],
            domain=monitoring_config['domain'],
            url=link,
            keywords=monitoring_config['keywords']
        )

        results.append(result)

# Aggregate and alert
critical_changes = [r for r in results if r.alert_criteria == "crit"]
if critical_changes:
    send_alert(critical_changes)
```

---

## 📊 Output Fields - Guaranteed

### Core Change Detection
- **`has_change`** (bool) - `true` if text differences or visual similarity < 98%
- **`similarity`** (float 0-1) - Overall similarity (60% text + 40% visual)
- **`text_added`** (int ≥ 0) - Number of words added
- **`text_removed`** (int ≥ 0) - Number of words removed
- **`total_diff_lines`** (int ≥ 0) - Total lines in unified diff

### Analysis & Summary
- **`summary_change`** (string, max 500 chars) - Natural language description
  - Example: "Content modified on regulatory page: 5 added, 2 removed. (7 diff lines)."

### Importance & Alerting
- **`importance`** (string) - One of: `"low"`, `"medium"`, `"critical"`
- **`import_score`** (float 0-10) - Numeric importance score
- **`alert_criteria`** (string) - One of: `"low"`, `"med"`, `"crit"`

### Score Mapping
| Score Range | Label | Alert |
|-------------|-------|-------|
| 0.0 - 4.4 | low | low |
| 4.5 - 7.4 | medium | med |
| 7.5 - 10.0 | critical | crit |

---

## 🎛️ Configuration

### Environment Variables
```bash
# LLM Configuration (default: disabled for deterministic behavior)
USE_BEDROCK=false
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0

# AWS Credentials (only if USE_BEDROCK=true)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

### Domain Weights
Domains have importance multipliers (configurable in `importance.py`):
```python
DomainWeights = {
    "regulatory": 1.2,   # 20% boost
    "safety": 1.15,      # 15% boost
    "pricing": 1.1,      # 10% boost
}
```

### Screenshot Handling
- **Empty string (`""`)**: Defaults to blank white 64x64 image (visual similarity = 1.0)
- **Bytes**: Raw image data (PNG, JPEG, etc.)
- **Base64 data URI**: `data:image/png;base64,...`
- **File path**: Local filesystem path

---

## ⚙️ Behavior Guarantees

### Deterministic Behavior
✅ When `USE_BEDROCK=false`:
- All operations are deterministic
- No network calls
- Same inputs → same outputs
- Fast execution (< 200ms typical)

### Fallback Strategy
✅ Graceful degradation:
1. LLM call attempted (if enabled)
2. If fails/disabled → deterministic fallback
3. Summary always generated
4. No request failures

### Error Handling
✅ Never fails the request:
- Invalid screenshots → use blank image
- HTML parse errors → extract what's possible
- LLM timeout → use fallback
- Always returns valid `ChangeResult`

---

## 📈 Performance Characteristics

| Metric | Typical Value | Max Value |
|--------|---------------|-----------|
| Response time (no LLM) | 100-200ms | 500ms |
| Response time (with LLM) | 1-3s | 5s |
| Memory usage | 10-20MB | 50MB |
| CPU usage | Low | Medium |

### Optimization Tips
1. **Batch processing**: Call in parallel for multiple pages
2. **Screenshot size**: Smaller images (< 1MB) process faster
3. **LLM usage**: Disable for dev/test, enable for production if needed

---

## 🧪 Testing

### Unit Tests
```bash
# All tests
pytest tests/unit/ -v

# Specific test
pytest tests/unit/test_pipeline_full.py -v

# Quick smoke test
pytest tests/unit/test_pipeline_full.py -q
```

### Integration Tests
```bash
# Start API server
uvicorn src.api.main:app --port 8080

# Test with curl
curl -X POST http://localhost:8080/v1/changes/analyze \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

---

## 🚨 Common Issues & Solutions

### Issue: `has_change=false` for obvious changes
**Cause:** Word-level comparison doesn't detect minor formatting changes
**Solution:**
- Check `similarity` value (should be < 1.0)
- Adjust threshold in pipeline: `has_change = (added + removed > 0) or (sim_visual < 0.95)`

### Issue: Importance score too high/low
**Cause:** Domain weight or keyword boost
**Solution:**
- Adjust domain weights in `importance.py`
- Review keyword list
- Check goal string (keywords match case-insensitive)

### Issue: Empty summary_change
**Cause:** Both DOMs identical or extraction failed
**Solution:**
- Verify DOMs are different
- Check for HTML parse errors in logs
- Ensure DOMs have visible text content

---

## 📞 Support & Escalation

### Team Contacts
- **Module Owner**: Mohit Tripathi (Platform Engineering)
- **Upstream (S3/DDB)**: Senior Engineer
- **Downstream (Orchestration)**: Orchestration Team
- **Current State**: Kotesh

### Escalation Path
1. Check logs for errors
2. Review test cases for similar scenarios
3. Verify input data format
4. Contact module owner if issue persists

### Telemetry (Safe for Logging)
These fields are safe to log (no PII):
- `url`
- `domain`
- `goal`
- `similarity`
- `import_score`
- `importance`
- `alert_criteria`
- `summary_change`

⚠️ **Do NOT log**:
- `prev_dom` / `cur_dom` (may contain PII)
- Screenshots (may contain sensitive data)

---

## 🎓 Quick Start Checklist

For integrators:

- [ ] Install package: `pip install -e .`
- [ ] Import function: `from change_analysis import analyze_change`
- [ ] Call with test data
- [ ] Verify all fields present in result
- [ ] Configure domain and keywords
- [ ] Set up monitoring/alerting based on `alert_criteria`
- [ ] Optionally enable LLM with `USE_BEDROCK=true`

---

## 📝 Change Log

### v1.0.0 (2025-10-27)
- Initial production release
- Full text + visual diff analysis
- Importance scoring with domain weights
- LLM integration with deterministic fallback
- HTTP API with FastAPI
- Comprehensive test suite

---

**Module Status:** ✅ Production-Ready
**Last Updated:** 2025-10-27
**Maintained By:** Platform Engineering Team
