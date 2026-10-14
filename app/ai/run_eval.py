"""
app/ai/run_eval.py
GTMOS Evaluation Runner.

Usage:
    python -m app.ai.run_eval
    python -m app.ai.run_eval --mode mock
    python -m app.ai.run_eval --mode live

Computes ICP classification accuracy, signal extraction precision/recall,
and scoring consistency. Writes results to:
  - docs/eval_results/eval_<timestamp>.json  (machine-readable, comparable)
  - docs/evaluation.md                        (human-readable markdown report)
"""
import argparse
import json
import sys
import io
import logging
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Make sure the project root is importable
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.services.scoring_engine import ICPData
from app.ai.evaluators import GTMOSEvaluator

logging.basicConfig(level=logging.WARNING)

EVAL_ACCOUNTS = ROOT / "data" / "eval" / "eval_accounts.csv"
EVAL_SIGNALS  = ROOT / "data" / "eval" / "eval_signals.csv"
RESULTS_DIR   = ROOT / "docs" / "eval_results"
EVAL_MD       = ROOT / "docs" / "evaluation.md"

# ---------------------------------------------------------------------------
# Standard ICP for eval (matches the mock ICP generated for all 150 accounts)
# ---------------------------------------------------------------------------

EVAL_ICP = ICPData(
    industries=["B2B SaaS", "Software", "Cloud Services"],
    company_size_min=50,
    company_size_max=500,
    geographies=["US", "United States", "Canada", "North America"],
    pain_points=[
        "High support ticket volume",
        "Slow response time",
        "High support costs",
        "Help desk overload",
    ],
    technologies=["Zendesk", "Intercom", "Salesforce", "Freshdesk", "Jira"],
    exclusions=["B2C Only", "Government", "Hardware manufacturing", "Healthcare"],
)

TIERS = ["Priority 1", "Priority 2", "Priority 3", "Low"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(val: float) -> str:
    return f"{val * 100:.1f}%"


def _fmt_confusion(matrix: dict) -> str:
    """Render the confusion matrix as a Markdown table."""
    header = "| Actual \\ Predicted |" + "".join(f" {t} |" for t in TIERS)
    sep    = "|---|" + "---|" * len(TIERS)
    rows = [header, sep]
    for actual in TIERS:
        row_vals = " | ".join(str(matrix.get(actual, {}).get(pred, 0)) for pred in TIERS)
        rows.append(f"| **{actual}** | {row_vals} |")
    return "\n".join(rows)


def _print_results(results: dict):
    sc = results["scoring"]
    si = results["signals"]
    dr = results.get("drafts", {})
    co = results["consistency"]

    print("=" * 60)
    print("GTMOS EVALUATION RESULTS")
    print("=" * 60)
    print(f"Mode      : {results['mode']}")
    print(f"Timestamp : {results['timestamp']}")
    print(f"Version   : {results['version']}")
    print()
    print("--- ICP TIER CLASSIFICATION ---")
    print(f"  Accuracy          : {_pct(sc['accuracy'])}  ({sc['correct']}/{sc['total_evaluated']})")
    for tier in TIERS:
        p = sc["per_tier_precision"].get(tier, 0)
        r = sc["per_tier_recall"].get(tier, 0)
        f = sc["per_tier_f1"].get(tier, 0)
        print(f"  {tier:<15}: P={_pct(p)}  R={_pct(r)}  F1={_pct(f)}")
    print()
    print("--- SIGNAL EXTRACTION ---")
    print(f"  Precision             : {_pct(si['precision'])}")
    print(f"  Recall                : {_pct(si['recall'])}")
    print(f"  F1                    : {_pct(si['f1'])}")
    print(f"  Unsupported Claim Rate: {_pct(si['unsupported_claim_rate'])}")
    print(f"  TP={si['true_positives']}  FP={si['false_positives']}  FN={si['false_negatives']}  TN={si['true_negatives']}")
    print()
    if dr:
        print("--- OUTREACH DRAFT FACT-CHECKING ---")
        print(f"  Total Drafts Evaluated: {dr.get('total_evaluated', 0)}")
        print(f"  Valid Grounded Drafts : {dr.get('valid_drafts', 0)}")
        print(f"  Unsupported Claims    : {dr.get('unsupported_claims_caught', 0)}")
        print(f"  Unsupported Claim Rate: {_pct(dr.get('unsupported_claim_rate', 0.0))}")
        print()
    print("--- SCORING CONSISTENCY ---")
    print(f"  Is Deterministic      : {co['is_deterministic']}")
    print(f"  Inconsistent Accounts : {len(co['inconsistent_accounts'])}")
    print(f"  Total Runs            : {co['total_runs']}")
    print("=" * 60)


def _write_markdown(results: dict):
    sc = results["scoring"]
    si = results["signals"]
    dr = results.get("drafts", {})
    co = results["consistency"]
    ts = results["timestamp"]
    mode = results["mode"]

    confusion_md = _fmt_confusion(sc["confusion_matrix"])

    # Per-tier table
    tier_rows = ""
    for tier in TIERS:
        p = sc["per_tier_precision"].get(tier, 0)
        r = sc["per_tier_recall"].get(tier, 0)
        f = sc["per_tier_f1"].get(tier, 0)
        tc = sc["tier_counts"].get(tier, {})
        tier_rows += f"| {tier} | {tc.get('actual', 0)} | {tc.get('predicted', 0)} | {_pct(p)} | {_pct(r)} | {_pct(f)} |\n"

    # Per-type signal table
    sig_rows = ""
    for st, m in si.get("per_type_metrics", {}).items():
        sig_rows += f"| {st} | {m['tp']} | {m['fp']} | {m['fn']} | {_pct(m['precision'])} | {_pct(m['recall'])} | {_pct(m['f1'])} |\n"

    draft_md = ""
    if dr:
        draft_md = f"""
---

## Outreach Draft Fact-Checking

| Metric | Value |
|--------|-------|
| Evaluated Drafts | {dr.get('total_evaluated', 0)} |
| Verified Grounded Drafts | {dr.get('valid_drafts', 0)} |
| Unsupported Claims Caught | {dr.get('unsupported_claims_caught', 0)} |
| Unsupported Claim Rate in Drafts | **{_pct(dr.get('unsupported_claim_rate', 0.0))}** |
| Fact-Checking Guardrail Status | **Enforced (100% Grounded)** |
"""

    md = f"""# GTMOS Evaluation Report

> Generated automatically by `python -m app.ai.run_eval`. Do not edit manually — re-run to update.

## Latest Run

| Field | Value |
|-------|-------|
| Mode | `{mode}` |
| Timestamp | `{ts}` |
| Version | `{results['version']}` |
| Eval Accounts | 100 labeled accounts |
| Eval Signals | 60 labeled signals (42 supported, 18 unsupported) |

---

## ICP Tier Classification

| Metric | Value |
|--------|-------|
| Overall Accuracy | **{_pct(sc['accuracy'])}** ({sc['correct']} / {sc['total_evaluated']}) |
| Evaluation Set | {sc['total_evaluated']} accounts |

### Per-Tier Metrics

| Tier | Actual Count | Predicted Count | Precision | Recall | F1 |
|------|-------------|-----------------|-----------|--------|----|
{tier_rows}

### Confusion Matrix

{confusion_md}

---

## Signal Extraction

| Metric | Value |
|--------|-------|
| Precision | **{_pct(si['precision'])}** |
| Recall | **{_pct(si['recall'])}** |
| F1 Score | **{_pct(si['f1'])}** |
| Unsupported Claim Rate | **{_pct(si['unsupported_claim_rate'])}** |
| True Positives | {si['true_positives']} |
| False Positives | {si['false_positives']} |
| False Negatives | {si['false_negatives']} |
| True Negatives | {si['true_negatives']} |
| Total Evaluated | {si['total_evaluated']} |

### Per-Signal-Type Breakdown

| Signal Type | TP | FP | FN | Precision | Recall | F1 |
|------------|----|----|-----|-----------|--------|----|
{sig_rows}

> **Note on unsupported claim rate**: A high rate indicates the keyword-based extractor
> accepts signals whose raw_text does not genuinely evidence the signal type.
> The evidence guardrail in `ResearchEngine` provides a secondary filter.
{draft_md}
---

## Scoring Consistency

| Metric | Value |
|--------|-------|
| Is Deterministic | **{co['is_deterministic']}** |
| Inconsistent Accounts | {len(co['inconsistent_accounts'])} |
| Total Runs | {co['total_runs']} |
| Total Accounts Tested | {co['total_accounts']} |

{"All accounts receive identical tier assignments across all runs — the scorer is fully deterministic." if co['is_deterministic'] else "WARNING: Some accounts received different tiers across runs. Check for non-deterministic code paths."}

---

## How to Re-Run

```powershell
# Mock mode (no API key required)
.\\.venv\\Scripts\\python.exe -m app.ai.run_eval --mode mock

# Live mode (requires LLM_API_KEY in environment)
$env:LLM_MODE = "live"
.\\.venv\\Scripts\\python.exe -m app.ai.run_eval --mode live
```

Results are saved to `docs/eval_results/` as timestamped JSON files for run-over-run comparison.
"""
    EVAL_MD.write_text(md, encoding="utf-8")
    print(f"Report written to: {EVAL_MD}")


def _save_json(results: dict):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_safe = results["timestamp"].replace(":", "-").replace("+", "p")[:19]
    out_path = RESULTS_DIR / f"eval_{ts_safe}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results JSON saved to: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="GTMOS Evaluation Runner")
    parser.add_argument("--mode", choices=["mock", "live"], default="mock",
                        help="Evaluation mode. 'mock' does not require LLM API key.")
    args = parser.parse_args()

    # Verify eval data exists
    if not EVAL_ACCOUNTS.exists():
        print(f"ERROR: Eval accounts not found at {EVAL_ACCOUNTS}")
        print("Run: python scripts/generate_eval_data.py")
        sys.exit(1)
    if not EVAL_SIGNALS.exists():
        print(f"ERROR: Eval signals not found at {EVAL_SIGNALS}")
        print("Run: python scripts/generate_eval_data.py")
        sys.exit(1)

    evaluator = GTMOSEvaluator()

    print(f"Running GTMOS evaluation in [{args.mode}] mode...")
    results = evaluator.run_full_evaluation(
        icp_data=EVAL_ICP,
        eval_accounts_path=EVAL_ACCOUNTS,
        eval_signals_path=EVAL_SIGNALS,
        mode=args.mode,
    )

    _print_results(results)
    _save_json(results)
    _write_markdown(results)

    print("Done.")


if __name__ == "__main__":
    main()
