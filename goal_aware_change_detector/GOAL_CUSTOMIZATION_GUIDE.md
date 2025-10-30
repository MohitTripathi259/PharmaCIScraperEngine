# Goal Customization Guide

## Where is the Goal Defined?

The goal is passed as a **command-line argument** (first parameter after the script name).

---

## Method 1: Direct Command Line

The simplest way - just change the goal string when running:

```bash
python compare_texts.py "YOUR GOAL HERE" prev.txt cur.txt
```

### Examples:

**Regulatory Monitoring:**
```bash
python compare_texts.py "Monitor regulatory submissions and FDA approvals" prev.txt cur.txt
```

**Safety Focus:**
```bash
python compare_texts.py "Track adverse events and safety signals" safety_prev.txt safety_cur.txt
```

**Financial Tracking:**
```bash
python compare_texts.py "Monitor R&D investments and program costs" financial_prev.txt financial_cur.txt
```

**Efficacy Monitoring:**
```bash
python compare_texts.py "Track response rates and survival endpoints" efficacy_prev.txt efficacy_cur.txt
```

**Operational Focus:**
```bash
python compare_texts.py "Monitor enrollment progress and site activation" operations_prev.txt operations_cur.txt
```

---

## Method 2: Edit run_with_bedrock.py

If you want to save a custom goal for repeated testing:

**File:** `run_with_bedrock.py`

**Line 14 - Change this:**
```python
# Original
"Monitor regulatory and clinical trial updates",  # ← CHANGE THIS LINE

# Examples of custom goals:
"Track patient enrollment and site metrics",
"Monitor drug safety and adverse event trends",
"Track competitive clinical trial landscape",
"Monitor protocol amendments and regulatory interactions",
```

### Full Example:

```python
"""Wrapper to run compare_texts.py with Bedrock enabled."""
import os
import sys
import subprocess

# Enable Bedrock
os.environ["USE_BEDROCK"] = "true"

# Run the comparison
result = subprocess.run(
    [
        sys.executable,
        "compare_texts.py",
        "Track patient safety and adverse event reporting",  # ← YOUR GOAL HERE
        "test_prev.txt",
        "test_cur.txt"
    ],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
)

# Write output to file
with open("updated_test_result_local.json", "w", encoding="utf-8") as f:
    f.write(result.stdout)
    if result.stderr:
        f.write("\n" + result.stderr)

# Also print to console
print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)

sys.exit(result.returncode)
```

---

## Method 3: Create Custom Test Scripts

Create different scripts for different monitoring goals:

### test_safety.py
```python
import os
import subprocess
import sys

os.environ["USE_BEDROCK"] = "true"

subprocess.run([
    sys.executable,
    "compare_texts.py",
    "Monitor adverse events, SAEs, and safety signals",  # Safety-focused goal
    "safety_prev.txt",
    "safety_cur.txt"
])
```

### test_regulatory.py
```python
import os
import subprocess
import sys

os.environ["USE_BEDROCK"] = "true"

subprocess.run([
    sys.executable,
    "compare_texts.py",
    "Track regulatory submissions, approvals, and agency interactions",  # Regulatory goal
    "regulatory_prev.txt",
    "regulatory_cur.txt"
])
```

### test_enrollment.py
```python
import os
import subprocess
import sys

os.environ["USE_BEDROCK"] = "true"

subprocess.run([
    sys.executable,
    "compare_texts.py",
    "Monitor patient enrollment rates, site activation, and recruitment challenges",  # Enrollment goal
    "enrollment_prev.txt",
    "enrollment_cur.txt"
])
```

---

## Method 4: Environment Variable (Advanced)

You can set a default goal via environment variable:

```bash
# Linux/Mac
export DEFAULT_GOAL="Monitor clinical trial milestones"
python compare_texts.py "$DEFAULT_GOAL" prev.txt cur.txt

# Windows PowerShell
$env:DEFAULT_GOAL="Monitor clinical trial milestones"
python compare_texts.py $env:DEFAULT_GOAL prev.txt cur.txt
```

---

## How the Goal Affects Analysis

The goal influences:

### 1. **Goal Alignment Score** (0.0-1.0)
- Higher alignment when changes match goal keywords
- Example: Goal = "Monitor safety" → SAE changes get higher alignment

### 2. **Domain Multiplier** (1.3x boost)
- Goals containing: "regulatory", "trial", "safety", "clinical"
- Get 1.3x importance score multiplier

### 3. **Keyword Extraction**
- Extracts keywords from goal (≥3 chars)
- Example: "Monitor regulatory submissions" → ["monitor", "regulatory", "submissions"]
- Text matching these keywords increases score

### 4. **LLM Summary Focus**
- Bedrock emphasizes changes relevant to the goal
- Example: Safety goal → highlights adverse events, SAE changes

---

## Example Goals by Use Case

### Clinical Monitoring
```
"Monitor patient enrollment, site activation, and trial milestones"
"Track protocol amendments and investigator communications"
"Monitor data monitoring committee findings and recommendations"
```

### Safety Surveillance
```
"Track adverse events, serious adverse events, and safety signals"
"Monitor drug-related toxicities and dose modifications"
"Track safety-related protocol amendments and regulatory notifications"
```

### Regulatory Affairs
```
"Monitor regulatory submissions, agency communications, and approvals"
"Track FDA interactions, clinical holds, and breakthrough designations"
"Monitor regulatory milestones and submission timelines"
```

### Financial/Operations
```
"Track R&D investments, program costs, and budget allocations"
"Monitor site payments, patient reimbursements, and operational expenses"
"Track vendor performance and contract modifications"
```

### Competitive Intelligence
```
"Monitor competitor trial progress and regulatory developments"
"Track competitive enrollment rates and site expansion"
"Monitor competitor protocol designs and endpoint selections"
```

---

## Testing Different Goals

### Quick Test with Different Goals

```bash
# Safety focus
python compare_texts.py "Monitor safety events" test_prev.txt test_cur.txt > safety_result.json

# Efficacy focus
python compare_texts.py "Track efficacy endpoints" test_prev.txt test_cur.txt > efficacy_result.json

# Regulatory focus
python compare_texts.py "Monitor regulatory progress" test_prev.txt test_cur.txt > regulatory_result.json
```

Compare the results to see how the goal affects:
- `goal_alignment` score
- `import_score` (if domain multiplier applies)
- Summary focus
- Key insights relevance

---

## Best Practices

### ✅ Good Goal Statements

**Specific and Actionable:**
- ✅ "Monitor Phase 3 enrollment and site activation"
- ✅ "Track SAE rates and safety-related protocol amendments"
- ✅ "Monitor regulatory submission timelines and agency feedback"

**Includes Key Metrics:**
- ✅ "Track enrollment rates, dropout rates, and completion percentages"
- ✅ "Monitor primary endpoint changes and statistical significance"

### ❌ Avoid Vague Goals

**Too Generic:**
- ❌ "Monitor everything"
- ❌ "Track changes"
- ❌ "Look at updates"

**Too Narrow:**
- ❌ "Monitor only SAE count" (misses context)
- ❌ "Track Phase number" (misses related changes)

---

## Quick Reference

| Task | Command |
|------|---------|
| **Change goal** | Edit first string argument in command |
| **Safety monitoring** | `"Monitor adverse events and safety signals"` |
| **Regulatory tracking** | `"Track FDA submissions and approvals"` |
| **Enrollment monitoring** | `"Monitor patient recruitment and site activation"` |
| **Financial tracking** | `"Track R&D spending and program costs"` |
| **Custom goal** | Just replace the goal string with your text |

---

## Example Session

```bash
# 1. Test with safety goal
python compare_texts.py "Monitor patient safety and adverse events" \
  safety_q3.txt safety_q4.txt

# 2. Same data, different goal (enrollment focus)
python compare_texts.py "Track patient enrollment and site metrics" \
  safety_q3.txt safety_q4.txt

# 3. Compare results - see how goal affects scoring and insights
cat result1.json | jq '.goal_alignment, .import_score'
cat result2.json | jq '.goal_alignment, .import_score'
```

---

**The goal is flexible - change it anytime to focus your analysis!**
