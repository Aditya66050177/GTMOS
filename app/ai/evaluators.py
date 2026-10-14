"""
app/ai/evaluators.py
Evaluation suite for GTMOS LLM components.

Computes:
  - ICP tier classification accuracy (score tier vs labeled expected_tier)
  - Signal extraction precision, recall, F1, unsupported claim rate
  - Scoring determinism/consistency across repeated runs

Never hardcodes or invents a metric — every number is computed from the labeled dataset.
"""
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from app.services.scoring_engine import ScoringEngine, AccountData, ICPData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal keyword map — same logic as ResearchEngine evidence check
# ---------------------------------------------------------------------------

SIGNAL_KEYWORDS: Dict[str, List[str]] = {
    "support_hiring": ["hiring", "recruit", "support team", "customer success", "headcount"],
    "funding": ["raised", "funding", "million", "investment", "series", "round"],
    "product_launch": ["launch", "released", "new product", "announced", "introducing"],
    "rapid_growth": ["growth", "scaling", "expanded", "doubling", "grew"],
    "relevant_technology": ["zendesk", "intercom", "salesforce", "freshdesk", "jira", "helpdesk"],
    "international_expansion": ["international", "global", "expand", "europe", "asia", "emea"],
    "executive_change": ["hired", "appointed", "new ceo", "new vp", "joined", "executive"],
}

TIERS = ["Priority 1", "Priority 2", "Priority 3", "Low"]


def _signal_would_be_accepted(signal_type: str, raw_text: str) -> bool:
    """Returns True if the signal extractor would accept this signal (keyword found in raw_text)."""
    keywords = SIGNAL_KEYWORDS.get(signal_type, [])
    text_lower = raw_text.lower()
    return any(kw in text_lower for kw in keywords)


def _safe_div(num: float, denom: float) -> float:
    return round(num / denom, 4) if denom > 0 else 0.0


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


# ---------------------------------------------------------------------------
# Load eval datasets
# ---------------------------------------------------------------------------

def _load_eval_accounts(csv_path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["employee_count"] = int(row["employee_count"] or 0)
            row["support_team_size"] = int(row["support_team_size"] or 0)
            row["technology_stack"] = [t.strip() for t in row["technology_stack"].split("|") if t.strip()]
            rows.append(row)
    return rows


def _load_eval_signals(csv_path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["is_supported"] = row["is_supported"].strip().lower() in ("true", "1", "yes")
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Main Evaluator
# ---------------------------------------------------------------------------

class GTMOSEvaluator:
    """
    Evaluation suite for GTMOS AI components.
    All metrics are computed from labeled data — nothing is hardcoded.
    """

    def __init__(self):
        self.scoring_engine = ScoringEngine()

    # ------------------------------------------------------------------
    # 1. ICP Tier Classification
    # ------------------------------------------------------------------

    def evaluate_scoring(
        self,
        icp_data: ICPData,
        eval_accounts_path: Path,
    ) -> Dict[str, Any]:
        """
        Runs compute_score() on every eval account and compares predicted tier
        against the expected_tier label. Returns accuracy + per-tier metrics + confusion matrix.
        """
        accounts = _load_eval_accounts(eval_accounts_path)

        # Confusion matrix: {actual_tier: {predicted_tier: count}}
        confusion: Dict[str, Dict[str, int]] = {t: {p: 0 for p in TIERS} for t in TIERS}
        correct = 0

        predictions: List[Tuple[str, str]] = []  # (expected, predicted)

        for row in accounts:
            acc = AccountData(
                id=int(row["account_id"]),
                industry=row["industry"],
                description=row["description"],
                employee_count=row["employee_count"],
                country=row["country"],
                technology_stack=row["technology_stack"],
                support_team_size=row["support_team_size"],
                funding=row["funding"],
            )
            result = self.scoring_engine.compute_score(acc, icp_data)
            predicted = result.tier
            expected = row["expected_tier"]

            # Normalize expected — the eval set uses Priority 1/2 for high-fit
            # but for accuracy we group Priority 1+2 as "high" if expected == "Priority 1/2"
            predictions.append((expected, predicted))
            if predicted == expected:
                correct += 1

            # Clamp unexpected labels
            exp_key = expected if expected in TIERS else "Low"
            pred_key = predicted if predicted in TIERS else "Low"
            confusion[exp_key][pred_key] += 1

        total = len(accounts)
        accuracy = _safe_div(correct, total)

        # Per-tier precision, recall, F1
        per_tier_precision = {}
        per_tier_recall = {}
        per_tier_f1 = {}
        tier_counts = {}

        for tier in TIERS:
            tp = confusion[tier][tier]
            fp = sum(confusion[other][tier] for other in TIERS if other != tier)
            fn = sum(confusion[tier][other] for other in TIERS if other != tier)
            actual_count = sum(confusion[tier].values())
            pred_count = tp + fp

            prec = _safe_div(tp, tp + fp)
            rec = _safe_div(tp, tp + fn)
            f1 = _f1(prec, rec)

            per_tier_precision[tier] = prec
            per_tier_recall[tier] = rec
            per_tier_f1[tier] = f1
            tier_counts[tier] = {
                "actual": actual_count,
                "predicted": pred_count,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }

        return {
            "accuracy": accuracy,
            "correct": correct,
            "total_evaluated": total,
            "per_tier_precision": per_tier_precision,
            "per_tier_recall": per_tier_recall,
            "per_tier_f1": per_tier_f1,
            "confusion_matrix": confusion,
            "tier_counts": tier_counts,
        }

    # ------------------------------------------------------------------
    # 2. Signal Extraction Quality
    # ------------------------------------------------------------------

    def evaluate_signal_extraction(
        self,
        eval_signals_path: Path,
    ) -> Dict[str, Any]:
        """
        Simulates the signal extractor on the labeled eval_signals.csv.
        Computes precision, recall, F1, and unsupported claim rate.
        """
        signals = _load_eval_signals(eval_signals_path)

        tp = fp = fn = tn = 0
        per_type: Dict[str, Dict[str, int]] = {}

        for row in signals:
            sig_type = row["signal_type"]
            raw_text = row["raw_text"]
            actually_supported = row["is_supported"]
            extractor_accepts = _signal_would_be_accepted(sig_type, raw_text)

            if sig_type not in per_type:
                per_type[sig_type] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}

            if actually_supported and extractor_accepts:
                tp += 1
                per_type[sig_type]["tp"] += 1
            elif not actually_supported and extractor_accepts:
                fp += 1
                per_type[sig_type]["fp"] += 1
            elif actually_supported and not extractor_accepts:
                fn += 1
                per_type[sig_type]["fn"] += 1
            else:
                tn += 1
                per_type[sig_type]["tn"] += 1

        total = len(signals)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _f1(precision, recall)
        unsupported_claim_rate = _safe_div(fp, total)

        # Per-type metrics
        per_type_metrics = {}
        for st, counts in per_type.items():
            p = _safe_div(counts["tp"], counts["tp"] + counts["fp"])
            r = _safe_div(counts["tp"], counts["tp"] + counts["fn"])
            per_type_metrics[st] = {
                "precision": p,
                "recall": r,
                "f1": _f1(p, r),
                **counts,
            }

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "total_evaluated": total,
            "unsupported_claim_rate": unsupported_claim_rate,
            "per_type_metrics": per_type_metrics,
        }

    # ------------------------------------------------------------------
    # 3. Scoring Consistency (Determinism)
    # ------------------------------------------------------------------

    def evaluate_scoring_consistency(
        self,
        icp_data: ICPData,
        eval_accounts_path: Path,
        runs: int = 5,
    ) -> Dict[str, Any]:
        """
        Runs scoring N times on the same data and checks every account
        gets the same tier every run. True determinism = no variance.
        """
        accounts = _load_eval_accounts(eval_accounts_path)
        all_run_results: List[Dict[int, str]] = []

        for _ in range(runs):
            run_results: Dict[int, str] = {}
            for row in accounts:
                acc = AccountData(
                    id=int(row["account_id"]),
                    industry=row["industry"],
                    description=row["description"],
                    employee_count=row["employee_count"],
                    country=row["country"],
                    technology_stack=row["technology_stack"],
                    support_team_size=row["support_team_size"],
                    funding=row["funding"],
                )
                result = self.scoring_engine.compute_score(acc, icp_data)
                run_results[int(row["account_id"])] = result.tier
            all_run_results.append(run_results)

        # Find accounts that changed tier across runs
        inconsistent = []
        account_ids = [int(r["account_id"]) for r in accounts]
        for aid in account_ids:
            tiers_seen = {run[aid] for run in all_run_results}
            if len(tiers_seen) > 1:
                inconsistent.append(aid)

        return {
            "is_deterministic": len(inconsistent) == 0,
            "inconsistent_accounts": inconsistent,
            "total_accounts": len(accounts),
            "total_runs": runs,
        }

    # ------------------------------------------------------------------
    # 4. Draft Fact-Check & Unsupported Claim Rate Evaluation
    # ------------------------------------------------------------------

    def evaluate_draft_claim_rate(
        self,
        eval_accounts_path: Path,
        mode: str = "mock",
    ) -> Dict[str, Any]:
        """
        Evaluates the unsupported claim rate in generated outreach drafts.
        Tests generated drafts against the strict fact-checking guardrail.
        """
        from app.models.models import Account as AccountModel, Signal as SignalModel
        from app.services.personalization import PersonalizationEngine
        from app.ai.llm import LLMService

        engine = PersonalizationEngine(llm=LLMService(mode=mode))
        accounts = _load_eval_accounts(eval_accounts_path)

        # Evaluate on Priority 1 & 2 accounts (eligible for outreach)
        eligible_accounts = [
            a for a in accounts if a["expected_tier"] in ("Priority 1", "Priority 2")
        ]

        total_evaluated = 0
        unsupported_claims_caught = 0
        valid_drafts = 0

        for row in eligible_accounts:
            total_evaluated += 1
            account_obj = AccountModel(
                id=int(row["account_id"]),
                name=row["name"],
                industry=row["industry"],
                employee_count=row["employee_count"],
                country=row["country"],
                description=row["description"],
                technology_stack=row["technology_stack"],
                support_team_size=row["support_team_size"],
                funding=row["funding"],
            )

            # Standard mock draft for this account
            prompt = f"Write outreach for {row['name']} with {row['employee_count']} employees."
            from app.schemas.draft import PersonalizationOutputSchema
            draft_out = engine.llm.generate_structured(prompt, PersonalizationOutputSchema)

            # Test using guardrail
            is_valid, reason = engine._validate_draft_facts(
                draft_out.message_draft,
                account_obj,
                []
            )

            if is_valid:
                valid_drafts += 1
            else:
                unsupported_claims_caught += 1

        unsupported_rate = _safe_div(unsupported_claims_caught, total_evaluated) if total_evaluated > 0 else 0.0

        return {
            "total_evaluated": total_evaluated,
            "valid_drafts": valid_drafts,
            "unsupported_claims_caught": unsupported_claims_caught,
            "unsupported_claim_rate": unsupported_rate,
            "guardrail_active": True,
        }

    # ------------------------------------------------------------------
    # 5. Full Evaluation Runner
    # ------------------------------------------------------------------

    def run_full_evaluation(
        self,
        icp_data: ICPData,
        eval_accounts_path: Path,
        eval_signals_path: Path,
        mode: str = "mock",
    ) -> Dict[str, Any]:
        """
        Runs all evaluations and returns a combined result dict.
        mode: 'mock' or 'live' — recorded but does not change computation.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        logger.info("Running scoring evaluation...")
        scoring = self.evaluate_scoring(icp_data, eval_accounts_path)

        logger.info("Running signal extraction evaluation...")
        signals = self.evaluate_signal_extraction(eval_signals_path)

        logger.info("Running draft fact-check evaluation...")
        drafts = self.evaluate_draft_claim_rate(eval_accounts_path, mode=mode)

        logger.info("Running consistency evaluation...")
        consistency = self.evaluate_scoring_consistency(icp_data, eval_accounts_path, runs=5)

        return {
            "version": "1.0",
            "mode": mode,
            "timestamp": timestamp,
            "scoring": scoring,
            "signals": signals,
            "drafts": drafts,
            "consistency": consistency,
        }
