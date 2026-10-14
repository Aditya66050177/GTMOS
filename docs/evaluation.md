# GTMOS Evaluation Report

> Generated automatically by `python -m app.ai.run_eval`. Do not edit manually — re-run to update.

## Latest Run

| Field | Value |
|-------|-------|
| Mode | `mock` |
| Timestamp | `2026-10-10T18:16:26.353500+00:00` |
| Version | `1.0` |
| Eval Accounts | 100 labeled accounts |
| Eval Signals | 60 labeled signals (42 supported, 18 unsupported) |

---

## ICP Tier Classification

| Metric | Value |
|--------|-------|
| Overall Accuracy | **57.0%** (57 / 100) |
| Evaluation Set | 100 accounts |

### Per-Tier Metrics

| Tier | Actual Count | Predicted Count | Precision | Recall | F1 |
|------|-------------|-----------------|-----------|--------|----|
| Priority 1 | 11 | 30 | 36.7% | 100.0% | 53.7% |
| Priority 2 | 19 | 2 | 0.0% | 0.0% | 0.0% |
| Priority 3 | 35 | 11 | 100.0% | 31.4% | 47.8% |
| Low | 35 | 57 | 61.4% | 100.0% | 76.1% |


### Confusion Matrix

| Actual \ Predicted | Priority 1 | Priority 2 | Priority 3 | Low |
|---|---|---|---|---|
| **Priority 1** | 11 | 0 | 0 | 0 |
| **Priority 2** | 19 | 0 | 0 | 0 |
| **Priority 3** | 0 | 2 | 11 | 22 |
| **Low** | 0 | 0 | 0 | 35 |

---

## Signal Extraction

| Metric | Value |
|--------|-------|
| Precision | **100.0%** |
| Recall | **100.0%** |
| F1 Score | **100.0%** |
| Unsupported Claim Rate | **0.0%** |
| True Positives | 42 |
| False Positives | 0 |
| False Negatives | 0 |
| True Negatives | 18 |
| Total Evaluated | 60 |

### Per-Signal-Type Breakdown

| Signal Type | TP | FP | FN | Precision | Recall | F1 |
|------------|----|----|-----|-----------|--------|----|
| international_expansion | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| funding | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| relevant_technology | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| product_launch | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| rapid_growth | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| support_hiring | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |
| executive_change | 6 | 0 | 0 | 100.0% | 100.0% | 100.0% |


> **Note on unsupported claim rate**: A high rate indicates the keyword-based extractor
> accepts signals whose raw_text does not genuinely evidence the signal type.
> The evidence guardrail in `ResearchEngine` provides a secondary filter.

---

## Outreach Draft Fact-Checking

| Metric | Value |
|--------|-------|
| Evaluated Drafts | 30 |
| Verified Grounded Drafts | 30 |
| Unsupported Claims Caught | 0 |
| Unsupported Claim Rate in Drafts | **0.0%** |
| Fact-Checking Guardrail Status | **Enforced (100% Grounded)** |

---

## Scoring Consistency

| Metric | Value |
|--------|-------|
| Is Deterministic | **True** |
| Inconsistent Accounts | 0 |
| Total Runs | 5 |
| Total Accounts Tested | 100 |

All accounts receive identical tier assignments across all runs — the scorer is fully deterministic.

---

## How to Re-Run

```powershell
# Mock mode (no API key required)
.\.venv\Scripts\python.exe -m app.ai.run_eval --mode mock

# Live mode (requires LLM_API_KEY in environment)
$env:LLM_MODE = "live"
.\.venv\Scripts\python.exe -m app.ai.run_eval --mode live
```

Results are saved to `docs/eval_results/` as timestamped JSON files for run-over-run comparison.
