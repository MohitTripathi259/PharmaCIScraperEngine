# Goal-Aware Text Change Detector

A minimal, production-ready text change detection system powered by AWS Bedrock (Claude) with intelligent local fallback.

## Overview

This tool compares two text documents and identifies changes that are **specifically relevant to your monitoring goal**. It uses advanced LLM reasoning (via AWS Bedrock) to understand context, semantics, and importance — or falls back to robust local analysis when Bedrock is unavailable.

## Features

✅ **Goal-Aware Analysis** - Changes are evaluated based on your specific monitoring objective
✅ **Smart Bedrock Integration** - Uses Claude for deep semantic understanding
✅ **Robust Local Fallback** - Works offline with difflib-based analysis
✅ **Structured Output** - JSON with importance scoring, similarity, insights, and reasoning
✅ **Production Ready** - Clean code, error handling, validation
✅ **Zero Dependencies** - Works without boto3 (local mode only)

## Quick Start

### 1. Installation

```bash
# No installation needed for local fallback mode!

# For Bedrock mode (optional):
pip install boto3
```

### 2. Test Locally (No AWS Required)

```bash
cd goal_aware_change_detector

python compare_texts.py "Monitor regulatory and clinical trial updates" test_prev.txt test_cur.txt
```

**Expected Output:**
```json
{
  "has_change": true,
  "summary_change": "Detected 104 token additions and 87 token removals. Overall similarity: 68.3%. Change significance: critical.",
  "text_added": 104,
  "text_removed": 87,
  "similarity": 0.683,
  "total_diff_lines": 45,
  "importance": "critical",
  "import_score": 8.5,
  "alert_criteria": "crit",
  "key_insights": [
    "Substantial content additions: 104 tokens added",
    "Substantial content removals: 87 tokens removed"
  ],
  "goal_alignment": 0.5,
  "reasoning": "Local heuristic analysis based on token-level diff. Score driven by 31.7% dissimilarity and 38.2% change ratio.",
  "llm_used": false
}
```

### 3. Test with AWS Bedrock (Cloud Mode)

```bash
# Windows PowerShell
$env:USE_BEDROCK="true"
$env:AWS_REGION="us-west-2"
$env:AWS_ACCESS_KEY_ID="your-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret"

python compare_texts.py "Monitor regulatory and clinical trial updates" test_prev.txt test_cur.txt
```

```bash
# Linux/Mac
export USE_BEDROCK=true
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret

python compare_texts.py "Monitor regulatory and clinical trial updates" test_prev.txt test_cur.txt
```

**Expected Output (with LLM):**
```json
{
  "has_change": true,
  "summary_change": "Critical regulatory progression from Phase 2 to Phase 3. Enrollment expanded from 450 to 800 patients across 120 sites (up from 67). SAE rate increased to 3.2%. Fast track designation received. Two programs discontinued.",
  "text_added": 112,
  "text_removed": 89,
  "similarity": 0.65,
  "total_diff_lines": 48,
  "importance": "critical",
  "import_score": 9.5,
  "alert_criteria": "crit",
  "key_insights": [
    "Phase advancement: Phase 2 → Phase 3 (critical milestone)",
    "Enrollment expansion: 450 → 800 patients, 67 → 120 sites",
    "SAE rate increase: 2.5% → 3.2%",
    "Fast track designation received from FDA",
    "Two oncology programs discontinued"
  ],
  "goal_alignment": 0.95,
  "reasoning": "Major regulatory progression with critical program changes. Phase advancement, fast track designation, and program discontinuations are highly relevant to regulatory and clinical trial monitoring goals.",
  "llm_used": true,
  "model_id": "anthropic.claude-3-5-sonnet-20240620-v1:0"
}
```

## Files

```
goal_aware_change_detector/
├── bedrock_prompt.py      # Bedrock prompt builder with sophisticated goal-aware templates
├── compare_texts.py       # Main script with Bedrock + local fallback logic
├── test_prev.txt          # Sample previous document (Phase 2 study)
├── test_cur.txt           # Sample current document (Phase 3 study)
└── README.md              # This file
```

## Usage

### Command Line

```bash
python compare_texts.py <goal> <prev_file> <cur_file>
```

**Arguments:**
- `goal` - Your monitoring objective (e.g., "Monitor regulatory updates", "Track financial metrics")
- `prev_file` - Path to previous/baseline text file
- `cur_file` - Path to current/new text file

**Examples:**

```bash
# Regulatory monitoring
python compare_texts.py "Monitor regulatory and clinical trial updates" prev.txt cur.txt

# Financial tracking
python compare_texts.py "Track quarterly financial performance" q2_report.txt q3_report.txt

# Safety surveillance
python compare_texts.py "Monitor adverse events and safety signals" prev_safety.txt cur_safety.txt

# Technical documentation
python compare_texts.py "Track API changes and breaking updates" v1_docs.txt v2_docs.txt
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_BEDROCK` | Enable AWS Bedrock (`true`/`false`) | `false` |
| `BEDROCK_MODEL_ID` | Claude model ID | `anthropic.claude-3-5-sonnet-20240620-v1:0` |
| `AWS_REGION` | AWS region | `us-west-2` |
| `AWS_ACCESS_KEY_ID` | AWS credentials | - |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | - |

## Output Schema

```json
{
  "has_change": boolean,           // True if meaningful changes detected
  "summary_change": "string",      // Concise summary of changes (200-300 chars)
  "text_added": int,               // Approximate tokens/words added
  "text_removed": int,             // Approximate tokens/words removed
  "similarity": float,             // 0.0-1.0 (1.0 = identical)
  "total_diff_lines": int,         // Number of changed lines
  "importance": "low|medium|critical",  // Categorical classification
  "import_score": float,           // 0.0-10.0 numeric importance
  "alert_criteria": "low|med|crit",     // Alert level
  "key_insights": ["strings"],     // 2-5 critical observations
  "goal_alignment": float,         // 0.0-1.0 relevance to goal (LLM only)
  "reasoning": "string",           // Justification of importance
  "llm_used": boolean,             // True if Bedrock was used
  "model_id": "string",            // Bedrock model ID (if used)
  "analysis_timestamp": "ISO8601"  // UTC timestamp
}
```

## How It Works

### Local Fallback Mode (Default)

When `USE_BEDROCK=false` or boto3 not installed:

1. **Token-level diff** using Python's `difflib.ndiff`
2. **Similarity calculation** using `SequenceMatcher`
3. **Heuristic scoring** based on dissimilarity and change ratio
4. **Fast and offline** - no API calls or network required

### Bedrock Mode (Cloud)

When `USE_BEDROCK=true` and AWS credentials configured:

1. **Smart prompt construction** with goal emphasis
2. **Claude API invocation** via AWS Bedrock
3. **Deep semantic analysis** - understands context, terminology, impact
4. **Goal-aware filtering** - prioritizes relevant changes
5. **Automatic fallback** to local mode if API fails

## Bedrock Prompt Design

The prompt template in `bedrock_prompt.py` is designed for maximum effectiveness:

✅ **System Instructions** - Defines Claude's role as comparative analyst
✅ **Goal Emphasis** - Repeated focus on monitoring objective
✅ **Step-by-Step Guidance** - Clear analytical workflow
✅ **Structured Output** - Strict JSON schema enforcement
✅ **Context Preservation** - Smart truncation keeps key details
✅ **Multi-Domain Support** - Works for any goal/domain

**Key Prompt Features:**
- Instructs Claude to detect semantic, numerical, terminology, and structural changes
- Requests goal-aligned filtering and relevance weighting
- Specifies importance classification criteria
- Enforces valid JSON output (no markdown, no commentary)
- Provides field definitions and value ranges

## Test Cases

The provided test files demonstrate critical changes:

**test_prev.txt (Q3 2025):**
- Phase 2 study
- 450 patients, 67 sites
- SAE rate 2.5%
- $10.3B R&D investment

**test_cur.txt (Q4 2025):**
- **Phase 3 trial** (critical progression)
- 800 patients, 120 sites (major expansion)
- SAE rate 3.2% (safety signal)
- $12.5B R&D investment (financial impact)
- **Fast track designation** (regulatory milestone)
- **Two programs discontinued** (portfolio change)

**Expected Classification:** CRITICAL (score 9-10) with LLM, CRITICAL (score 8-9) with local fallback

## AWS Bedrock Setup

### Prerequisites

1. AWS account with Bedrock access
2. Model access enabled for Claude 3.5 Sonnet
3. IAM credentials with bedrock:InvokeModel permission

### Enable Bedrock Access

```bash
# 1. AWS Console → Bedrock → Model access → Request access
#    Select: Claude 3.5 Sonnet

# 2. Create IAM user with policy:
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "bedrock:InvokeModel",
    "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
  }]
}

# 3. Set credentials
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-west-2
export USE_BEDROCK=true
```

## Cost Considerations

### Local Fallback Mode
- **Cost:** $0 (completely free)
- **Speed:** < 0.1 seconds
- **Quality:** Good for straightforward diffs

### Bedrock Mode
- **Cost:** ~$0.003 per analysis (Claude 3.5 Sonnet pricing)
- **Speed:** 1-3 seconds
- **Quality:** Excellent for semantic, goal-aware analysis

**Recommendation:** Use local mode for development/testing, Bedrock for production.

## Troubleshooting

### "boto3 not installed" Warning

**Solution:** This is normal for local fallback mode. Install boto3 only if you need Bedrock:
```bash
pip install boto3
```

### "Bedrock failed → fallback used"

**Possible causes:**
1. AWS credentials not configured
2. Model access not enabled in AWS Console
3. Wrong region or model ID
4. IAM permissions insufficient

**Solution:** Check environment variables and AWS setup

### JSON Parsing Errors

**Cause:** Claude sometimes returns markdown code fences
**Solution:** The `coerce_json()` function handles this automatically

## Advanced Usage

### Programmatic Usage

```python
from pathlib import Path
from compare_texts import run_bedrock_analysis
import json

goal = "Monitor safety and efficacy changes"
prev_text = Path("prev.txt").read_text()
cur_text = Path("cur.txt").read_text()

result = run_bedrock_analysis(goal, prev_text, cur_text)

print(f"Importance: {result['importance']}")
print(f"Score: {result['import_score']}/10")
print(f"Summary: {result['summary_change']}")
```

### Custom Bedrock Models

```bash
# Use Claude 3 Opus for highest quality
export BEDROCK_MODEL_ID="anthropic.claude-3-opus-20240229-v1:0"

# Use Claude 3 Haiku for fastest/cheapest
export BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
```

## Comparison with Previous System

| Feature | Previous System | Goal-Aware Detector |
|---------|----------------|---------------------|
| LLM Integration | Optional fallback | Primary with fallback |
| Goal Awareness | Limited | Core feature |
| Prompt Quality | Basic | Sophisticated |
| Local Mode | Basic heuristics | Token-level diff |
| Output | Basic metrics | Rich insights + reasoning |
| Dependencies | Many | Just boto3 (optional) |
| Setup Complexity | High | Minimal |

## Support

For issues or questions:
1. Check this README first
2. Review test files for examples
3. Enable debug output: `python -u compare_texts.py ...`

## License

Internal Pfizer use only.
