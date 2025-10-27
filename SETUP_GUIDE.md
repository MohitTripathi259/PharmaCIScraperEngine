# Setup & Testing Guide

This guide provides step-by-step instructions for setting up and testing the Change Analysis module.

## Prerequisites

- Python 3.11 or higher
- pip (latest version recommended)
- Optional: Python virtual environment

## Setup Instructions

### Option 1: Using a Virtual Environment (Recommended)

#### On Windows (PowerShell)
```powershell
# Create virtual environment
python -m venv .venv311

# Activate virtual environment
.\.venv311\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install project in editable mode (includes all dependencies)
pip install -e .

# Or install with optional dependencies
pip install -e ".[test,aws]"
```

#### On Linux/macOS (Bash)
```bash
# Create virtual environment
python3.11 -m venv .venv311

# Activate virtual environment
source .venv311/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install project in editable mode
pip install -e .
```

### Option 2: System-Wide Installation

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install in editable mode
pip install -e .
```

## Verify Installation

### 1. Run Unit Tests

```bash
# Quick test (quiet mode)
python -m pytest -q tests/unit/test_change_analysis.py

# Verbose output
python -m pytest -v tests/unit/test_change_analysis.py

# With coverage report
python -m pytest --cov=src/change_analysis tests/unit/test_change_analysis.py -v
```

**Expected Output:**
```
============================= 22 passed in 0.57s ==============================
```

### 2. Run Demo Script

```bash
python demo.py
```

**Expected Output:**
- Screenshot creation messages
- Analysis results with importance score
- JSON output
- Success confirmation

### 3. Test Python API

```python
from change_analysis import analyze_change

result = analyze_change(
    prev_dom="<html><body><h1>Version 1</h1></body></html>",
    cur_dom="<html><body><h1>Version 2</h1></body></html>",
    prev_ss=b"",  # Can use bytes, file path, or data URI
    cur_ss=b"",
    goal="Monitor changes",
    domain="general",
    url="https://example.com"
)

print(f"Change detected: {result.has_change}")
print(f"Importance: {result.importance}")
print(f"Score: {result.import_score}/10")
```

## Start HTTP API Server

### Basic Startup

```bash
# Default port (8000)
python -m uvicorn src.api.main:app

# Custom port
python -m uvicorn src.api.main:app --port 8080

# With auto-reload (development mode)
python -m uvicorn src.api.main:app --reload --port 8080
```

### Production Startup

```bash
# With multiple workers
python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 4 \
    --log-level info
```

## Test API Endpoints

### Using curl (Linux/macOS/Git Bash)

```bash
# Health check
curl http://localhost:8080/health

# Analyze change
curl -X POST http://localhost:8080/v1/changes/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "prev_dom": "<html><body><h1>Trial 3</h1></body></html>",
    "cur_dom": "<html><body><h1>Trial 4</h1></body></html>",
    "prev_ss": "",
    "cur_ss": "",
    "goal": "Track new trials and approvals",
    "domain": "regulatory",
    "url": "https://example.com",
    "keywords": ["trial", "phase", "approval", "fda"]
  }'
```

### Using PowerShell (Windows)

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8080/health"

# Analyze change
$payload = @{
  prev_dom = "<html><body><h1>Trial 3</h1></body></html>"
  cur_dom  = "<html><body><h1>Trial 4</h1></body></html>"
  prev_ss  = ""
  cur_ss   = ""
  goal     = "Track new trials and approvals"
  domain   = "regulatory"
  url      = "https://example.com"
  keywords = @("trial", "phase", "approval", "fda")
} | ConvertTo-Json

Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8080/v1/changes/analyze" `
  -ContentType "application/json" `
  -Body $payload
```

### Using test_request.json File

```bash
# Create test file (already included in project)
# Then run:
curl -X POST http://localhost:8080/v1/changes/analyze \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

**Expected Response:**
```json
{
  "has_change": true,
  "text_added": 1,
  "text_removed": 1,
  "similarity": 0.9143,
  "total_diff_lines": 2,
  "summary_change": "Content modified on regulatory page: 1 lines added, 1 lines removed",
  "importance": "low",
  "import_score": 1.63,
  "alert_criteria": "low"
}
```

## Interactive API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json

## Configuration

### Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Enable LLM summarization (requires AWS credentials)
USE_BEDROCK=true
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0

# AWS credentials (if not using ~/.aws/credentials)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### Verify Configuration

```python
import os
print(f"USE_BEDROCK: {os.getenv('USE_BEDROCK', 'false')}")
print(f"BEDROCK_MODEL_ID: {os.getenv('BEDROCK_MODEL_ID', 'default')}")
```

## Troubleshooting

### Import Errors

If you get import errors like `ModuleNotFoundError: No module named 'change_analysis'`:

1. Ensure you've installed the package: `pip install -e .`
2. Verify installation: `pip list | grep change-analysis`
3. Check Python path: `python -c "import sys; print(sys.path)"`

### Port Already in Use

If you get "Address already in use" error:

```bash
# Use a different port
python -m uvicorn src.api.main:app --port 8081

# Or find and kill the process using the port
# Windows:
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/macOS:
lsof -ti:8080 | xargs kill -9
```

### Screenshot Loading Errors

When providing empty strings for screenshots (`prev_ss=""`, `cur_ss=""`):
- The system gracefully handles this by assuming visual similarity = 1.0
- To avoid this warning, either:
  - Provide valid file paths
  - Provide base64 data URIs
  - Provide raw bytes

### AWS Bedrock Errors

If LLM calls fail:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify IAM permissions for Bedrock
3. Ensure model is available in your region
4. Set `USE_BEDROCK=false` to use local fallback

### Test Failures

If tests fail:
1. Ensure all dependencies installed: `pip install -e ".[test]"`
2. Check Python version: `python --version` (should be 3.11+)
3. Clear pytest cache: `rm -rf .pytest_cache`
4. Run with verbose output: `pytest -vv tests/`

## Development Workflow

### Making Code Changes

Since the package is installed in editable mode (`pip install -e .`), code changes are immediately reflected:

1. Edit source files in `src/change_analysis/`
2. Run tests: `pytest tests/unit/test_change_analysis.py`
3. Test manually: `python demo.py`
4. Restart API server if needed (or use `--reload` flag)

### Adding Dependencies

1. Edit `pyproject.toml` under `[project] dependencies`
2. Reinstall: `pip install -e .`

### Running Type Checks (Optional)

```bash
# Install mypy
pip install mypy

# Run type checking
mypy src/change_analysis --strict
```

### Code Formatting (Optional)

```bash
# Install formatters
pip install black isort

# Format code
black src/ tests/
isort src/ tests/
```

## Performance Benchmarking

```bash
# Time the tests
time python -m pytest tests/unit/test_change_analysis.py

# Profile the demo
python -m cProfile -s cumulative demo.py

# API load test (requires Apache Bench)
ab -n 100 -c 10 -p test_request.json -T application/json \
   http://localhost:8080/v1/changes/analyze
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[test]"
      - run: pytest tests/unit/test_change_analysis.py -v
```

## Support

For issues or questions:
1. Check this guide first
2. Review README.md and PROJECT_SUMMARY.md
3. Check test cases in `tests/unit/test_change_analysis.py`
4. Contact the Platform Engineering team

## Quick Reference Commands

```bash
# Install
pip install -e .

# Test
pytest -q tests/unit/test_change_analysis.py

# Demo
python demo.py

# API (development)
uvicorn src.api.main:app --reload --port 8080

# API (production)
uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --workers 4

# Health check
curl http://localhost:8080/health

# Test endpoint
curl -X POST http://localhost:8080/v1/changes/analyze \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

---

**Last Updated:** 2025-10-27
**Version:** 1.0.0
