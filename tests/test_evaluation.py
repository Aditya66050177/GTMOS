"""
tests/test_evaluation.py
Tests for the Phase 5 evaluation suite (GTMOSEvaluator).
Verifies that evaluation metrics are computed accurately from data and determinism is upheld.
"""
from pathlib import Path
import pytest

from app.services.scoring_engine import ICPData
from app.ai.evaluators import GTMOSEvaluator

ROOT = Path(__file__).parent.parent
EVAL_ACCOUNTS = ROOT / "data" / "eval" / "eval_accounts.csv"
EVAL_SIGNALS = ROOT / "data" / "eval" / "eval_signals.csv"

EVAL_ICP = ICPData(
    industries=["B2B SaaS", "Software", "Cloud Services"],
    company_size_min=50,
    company_size_max=500,
    geographies=["US", "United States", "Canada", "North America"],
    pain_points=["High support ticket volume", "Slow response time", "High support costs"],
    technologies=["Zendesk", "Intercom", "Salesforce", "Freshdesk", "Jira"],
    exclusions=["B2C Only", "Government", "Hardware manufacturing", "Healthcare"],
)


def test_evaluator_scoring_metrics():
    evaluator = GTMOSEvaluator()
    result = evaluator.evaluate_scoring(EVAL_ICP, EVAL_ACCOUNTS)

    assert result["total_evaluated"] == 100
    assert 0.0 <= result["accuracy"] <= 1.0
    assert "confusion_matrix" in result
    assert "per_tier_precision" in result
    assert "per_tier_recall" in result


def test_evaluator_signal_metrics():
    evaluator = GTMOSEvaluator()
    result = evaluator.evaluate_signal_extraction(EVAL_SIGNALS)

    assert result["total_evaluated"] == 60
    assert result["true_positives"] == 42
    assert result["true_negatives"] == 18
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["unsupported_claim_rate"] == 0.0


def test_evaluator_draft_claim_rate():
    evaluator = GTMOSEvaluator()
    result = evaluator.evaluate_draft_claim_rate(EVAL_ACCOUNTS, mode="mock")

    assert result["total_evaluated"] > 0
    assert result["valid_drafts"] == result["total_evaluated"]
    assert result["unsupported_claim_rate"] == 0.0


def test_evaluator_scoring_consistency():
    evaluator = GTMOSEvaluator()
    result = evaluator.evaluate_scoring_consistency(EVAL_ICP, EVAL_ACCOUNTS, runs=3)

    assert result["is_deterministic"] is True
    assert len(result["inconsistent_accounts"]) == 0
    assert result["total_runs"] == 3


def test_full_evaluation_runner():
    evaluator = GTMOSEvaluator()
    full_result = evaluator.run_full_evaluation(
        EVAL_ICP,
        EVAL_ACCOUNTS,
        EVAL_SIGNALS,
        mode="mock"
    )

    assert full_result["mode"] == "mock"
    assert full_result["version"] == "1.0"
    assert "scoring" in full_result
    assert "signals" in full_result
    assert "drafts" in full_result
    assert "consistency" in full_result
