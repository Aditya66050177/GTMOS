from dataclasses import dataclass
from typing import List, Optional, Any
from app.models import Score, Signal, ICPProfile
from app.schemas.scoring import ScoreResult

# Mapping table for signal types to angles
SIGNAL_TO_ANGLE = {
    "support_hiring": "support team scaling and efficiency",
    "funding": "post-funding growth and tooling",
    "product_launch": "supporting new product rollouts",
    "international_expansion": "managing global operations and localization",
    "relevant_technology": "integrating with your existing tech stack",
    "rapid_growth": "handling increased volume at scale",
    "executive_change": "new strategic initiatives",
}

@dataclass
class RecommendationResult:
    action: str
    reason: str
    suggested_persona: Optional[str]
    suggested_angle: Optional[str]

class RecommendationEngine:
    """
    Deterministic rule-based engine to recommend the next best action.
    Rules use deterministic templates and mapping tables, not LLM generations.
    """
    def get_recommendation(
        self,
        score: Any,
        signals: List[Any],
        icp: Optional[Any] = None
    ) -> RecommendationResult:
        # Normalize score inputs (works with Score model or ScoreResult)
        tier = getattr(score, "tier", "Low")
        intent_score = getattr(score, "intent_score", 0.0) or 0.0

        # Find strongest positive signal
        strongest_signal = None
        for sig in (signals or []):
            stype = getattr(sig, "signal_type", None) or getattr(sig, "type", None)
            strength = getattr(sig, "strength", 0.0) or 0.0
            if stype in SIGNAL_TO_ANGLE and strength > 0:
                if not strongest_signal or strength > (getattr(strongest_signal, "strength", 0.0) or 0.0):
                    strongest_signal = sig

        strongest_type = (
            getattr(strongest_signal, "signal_type", None) or getattr(strongest_signal, "type", None)
            if strongest_signal else None
        )

        # 1. Action & Reason (Deterministic Rules)
        if tier == "Priority 1":
            if intent_score >= 10.0:
                action = "CONTACT"
                reason = "Priority 1 account with strong intent signals detected."
            else:
                action = "RESEARCH"
                reason = "Priority 1 account but lacking strong intent. Research for recent triggers."
        elif tier == "Priority 2":
            if intent_score >= 15.0:
                action = "PRIORITIZE"
                reason = "Priority 2 account with very high intent. Prioritize for immediate outreach."
            elif intent_score >= 5.0:
                action = "NURTURE"
                reason = "Priority 2 account with moderate intent. Nurture until strong buying triggers emerge."
            else:
                action = "RESEARCH"
                reason = "Priority 2 account with weak intent. Research to find active buying signals."
        elif tier == "Priority 3":
            if intent_score >= 10.0:
                action = "NURTURE"
                reason = "Priority 3 account showing some buying signals. Add to automated nurture sequence."
            else:
                action = "DEPRIORITIZE"
                reason = "Priority 3 account with weak intent. Deprioritize for direct outreach."
        else: # Low tier
            action = "DEPRIORITIZE"
            reason = "Low fit account. Disqualify or deprioritize."

        # 2. Suggested Persona (derived from ICP buyer roles & strongest signal)
        suggested_persona = None
        buyer_roles = []
        if icp:
            buyer_roles = getattr(icp, "buyer_roles", []) or []

        if buyer_roles:
            if strongest_type == "support_hiring":
                suggested_persona = next((r for r in buyer_roles if any(k in r.lower() for k in ["support", "experience", "cx", "customer"])), buyer_roles[0])
            elif strongest_type in ["funding", "rapid_growth"]:
                suggested_persona = next((r for r in buyer_roles if any(k in r.lower() for k in ["revenue", "cro", "sales", "ceo", "growth"])), buyer_roles[0])
            elif strongest_type in ["product_launch", "relevant_technology"]:
                suggested_persona = next((r for r in buyer_roles if any(k in r.lower() for k in ["product", "engineering", "tech", "cto", "operations"])), buyer_roles[0])
            else:
                suggested_persona = buyer_roles[0]
        else:
            suggested_persona = "VP of Customer Support"

        # 3. Suggested Angle
        if strongest_type and strongest_type in SIGNAL_TO_ANGLE:
            suggested_angle = SIGNAL_TO_ANGLE[strongest_type]
        else:
            suggested_angle = "support team scaling and efficiency"

        return RecommendationResult(
            action=action,
            reason=reason,
            suggested_persona=suggested_persona,
            suggested_angle=suggested_angle
        )
