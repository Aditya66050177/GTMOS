from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.core.timeutil import utc_now
from app.models import Account, ICPProfile, Product, Signal
from app.services.signal_config import SIGNAL_WEIGHTS

NEGATIVE_SOURCE = "Internal CRM"
_ALWAYS_OK_GEOS = ["us", "united states", "usa", "ca", "canada", "uk", "united kingdom", "gb"]
_TECH_INDUSTRY_KEYWORDS = ["software", "saas", "tech", "cloud"]


def derive_negative_signals(
    employee_count: Optional[int],
    industry: Optional[str],
    country: Optional[str],
    description: Optional[str],
    icp: Any,
) -> List[Dict[str, Any]]:
    """Pure rules: which disqualifying signals does this account trigger against the ICP?"""
    negatives: List[Dict[str, Any]] = []

    emp = employee_count or 0
    min_emp = getattr(icp, "company_size_min", None) or 50
    if 0 < emp < min_emp:
        negatives.append({
            "signal_type": "too_small",
            "description": f"Company size ({emp}) is below ICP minimum ({min_emp}).",
            "evidence": f"employee_count={emp}",
        })

    acc_ind = (industry or "").strip().lower()
    icp_inds = [i.strip().lower() for i in (getattr(icp, "industries", None) or [])]
    if acc_ind and acc_ind not in icp_inds and not any(kw in acc_ind for kw in _TECH_INDUSTRY_KEYWORDS):
        negatives.append({
            "signal_type": "wrong_industry",
            "description": f"Industry '{industry}' does not match ICP.",
            "evidence": f"industry={industry}",
        })

    acc_geo = (country or "").strip().lower()
    icp_geos = [g.strip().lower() for g in (getattr(icp, "geographies", None) or [])]
    if acc_geo and not any(g in acc_geo or acc_geo in g for g in icp_geos) and acc_geo not in _ALWAYS_OK_GEOS:
        negatives.append({
            "signal_type": "wrong_geography",
            "description": f"Country '{country}' is outside target ICP regions.",
            "evidence": f"country={country}",
        })

    desc = (description or "").lower()
    exclusions = getattr(icp, "exclusions", None) or getattr(icp, "exclusion_criteria", None) or []
    for ex in (e.lower() for e in exclusions):
        if ex in acc_ind or ex in desc:
            negatives.append({
                "signal_type": "no_use_case",
                "description": f"Matched exclusion criterion: '{ex}'",
                "evidence": f"description matched {ex}",
            })
            break

    return negatives


def _field(sig: Any, name: str, default: Any = None) -> Any:
    if isinstance(sig, dict):
        return sig.get(name, default)
    return getattr(sig, name, default)


def recency_decay(days_old: int) -> float:
    if days_old > 180:
        return 0.0
    if days_old > 90:
        return 0.5
    return 1.0


def score_signals(signals: Iterable[Any], now: Optional[datetime] = None) -> float:
    """Pure intent score /20: keep the newest signal per type, weight, decay, clamp."""
    now = now or utc_now()
    best: Dict[str, Any] = {}
    for sig in signals:
        stype = _field(sig, "signal_type")
        current = best.get(stype)
        if current is None:
            best[stype] = sig
            continue
        new_at, cur_at = _field(sig, "detected_at"), _field(current, "detected_at")
        if new_at and cur_at and new_at > cur_at:
            best[stype] = sig

    raw_score = 0.0
    for sig in best.values():
        weight = SIGNAL_WEIGHTS.get(_field(sig, "signal_type"), 0.0)
        if weight == 0.0:
            continue
        detected_at = _field(sig, "detected_at")
        days_old = (now - detected_at).days if detected_at else 0
        strength = _field(sig, "strength")
        confidence = _field(sig, "confidence")
        strength = 1.0 if strength is None else strength
        confidence = 1.0 if confidence is None else confidence
        raw_score += weight * strength * confidence * recency_decay(days_old)

    return min(20.0, max(0.0, raw_score))


class SignalEngine:

    def _add_negative_signals(self, db: Session, account: Account, icp: ICPProfile) -> List[Signal]:
        """
        Deterministically derive negative signals based on the account vs ICP profile.
        These are generated on-the-fly and appended to the DB to ensure fresh intent scores.
        """
        now = utc_now()
        negatives = [
            Signal(
                account_id=account.id,
                strength=1.0,
                source=NEGATIVE_SOURCE,
                detected_at=now,
                confidence=1.0,
                **neg,
            )
            for neg in derive_negative_signals(
                account.employee_count, account.industry, account.country, account.description, icp
            )
        ]

        # Remove existing deterministically generated negative signals to replace them
        existing_negatives = db.query(Signal).filter(
            Signal.account_id == account.id,
            Signal.source == NEGATIVE_SOURCE,
        ).all()
        for en in existing_negatives:
            db.delete(en)

        for n in negatives:
            db.add(n)
        db.commit()
        return negatives

    def calculate_intent(self, db: Session, account: Account, product: Product) -> float:
        """
        Normalizes signals, deduplicates, applies recency decay, and outputs intent score / 20.
        """
        icp = db.query(ICPProfile).filter_by(product_id=product.id).first()
        if not icp:
            return 0.0

        self._add_negative_signals(db, account, icp)
        signals = db.query(Signal).filter_by(account_id=account.id).all()
        return score_signals(signals, utc_now())
