"""Everything the methodology page shows, read from the code and computed from the labelled data.

Nothing here is hand-typed numbers: weights, thresholds and rules come from the
modules that use them, and evaluation metrics are computed on each call with the
existing GTMOSEvaluator on data/eval (about 10 ms).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.ai.evaluators import GTMOSEvaluator
from app.ai.run_eval import EVAL_ICP
from app.services.recommendation_engine import ACTION_RULES
from app.services.scoring_engine import TIER_THRESHOLDS
from app.services.signal_config import SIGNAL_WEIGHTS
from app.services.signal_engine import AGING_AFTER_DAYS, AGING_DECAY, EXPIRED_AFTER_DAYS, INTENT_MAX

EVAL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "eval"

# Maximum points per component, as defined in ScoringEngine.compute_score.
COMPONENTS = [
    {"name": "ICP fit", "max": 30, "part_of": "fit",
     "rule": "Industry: exact match 20, adjacent 10, else 0. Plus up to 10 for overlap with the ICP's pain points."},
    {"name": "Company fit", "max": 20, "part_of": "fit",
     "rule": "Employee count inside the ICP range 20, within 25% of it 10, else 0. A matched exclusion subtracts 20."},
    {"name": "Technology fit", "max": 15, "part_of": "fit",
     "rule": "Share of the ICP's tools the company runs, scaled to 15."},
    {"name": "Geography fit", "max": 15, "part_of": "fit",
     "rule": "Country in the target list 15, in the target region 8, else 0."},
    {"name": "Buying intent", "max": 20, "part_of": "intent",
     "rule": "Verified signals: weight x strength x confidence x recency decay, newest per type, minus disqualifier penalties, clamped to 0-20."},
]

REJECTION_CATEGORIES = {
    "negated": "The claim is explicitly contradicted (\"not hiring\", \"hiring freeze\").",
    "unsupported": "Hearsay (\"rumours suggest\") or the quoted evidence is not in the source text.",
    "ambiguous": "Speculative wording about a signal topic with no concrete event (\"looking into\", \"might\").",
}


def methodology() -> Dict[str, Any]:
    evaluator = GTMOSEvaluator()
    scoring = evaluator.evaluate_scoring(EVAL_ICP, EVAL_DIR / "eval_accounts.csv")
    signals = evaluator.evaluate_signal_extraction(EVAL_DIR / "eval_signals.csv")
    return {
        "components": COMPONENTS,
        "fit_max": sum(c["max"] for c in COMPONENTS if c["part_of"] == "fit"),
        "intent_max": INTENT_MAX,
        "signal_weights": {k: v for k, v in SIGNAL_WEIGHTS.items() if v > 0},
        "disqualifier_penalties": {k: v for k, v in SIGNAL_WEIGHTS.items() if v < 0},
        "decay": {"current_max_days": AGING_AFTER_DAYS, "aging_max_days": EXPIRED_AFTER_DAYS, "aging_decay": AGING_DECAY},
        "tiers": [{"tier": t, "min_total": m} for t, m in TIER_THRESHOLDS],
        "action_rules": [{"rule_id": rid, "tier": t, "condition": c, "action": a} for rid, (t, c, a) in ACTION_RULES.items()],
        "rejection_categories": REJECTION_CATEGORIES,
        "evaluation": {
            "tier": {
                "accuracy": scoring["accuracy"], "correct": scoring["correct"], "total": scoring["total_evaluated"],
                "precision": scoring["per_tier_precision"], "recall": scoring["per_tier_recall"],
                "confusion_matrix": scoring["confusion_matrix"], "tier_counts": scoring.get("tier_counts"),
                "method": ("100 labelled synthetic accounts (data/eval/eval_accounts.csv) scored with the same "
                           "compute_score() rules. These accounts have no research notes, so intent comes from the "
                           "engine's built-in proxy (support team size and funding stage, up to 20 points), not from "
                           "verified signals as in the demo."),
            },
            "signals": {
                "precision": signals["precision"], "recall": signals["recall"], "f1": signals["f1"],
                "total": signals["total_evaluated"], "unsupported_claim_rate": signals["unsupported_claim_rate"],
                "method": ("60 labelled synthetic sentences (data/eval/eval_signals.csv) checked with a simplified "
                           "keyword matcher, not the production extractor. The 100% scores describe that matcher on "
                           "easy synthetic text and should not be read as real-world extraction quality."),
            },
        },
    }
