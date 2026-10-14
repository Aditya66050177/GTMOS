from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models import Account, Signal, ICPProfile, Product
from app.services.signal_config import SIGNAL_WEIGHTS

class SignalEngine:
    def _add_negative_signals(self, db: Session, account: Account, icp: ICPProfile) -> List[Signal]:
        """
        Deterministically derive negative signals based on the account vs ICP profile.
        These are generated on-the-fly and appended to the DB to ensure fresh intent scores.
        """
        negatives = []
        now = datetime.utcnow()
        
        # 1. Too small
        emp = account.employee_count or 0
        min_emp = icp.company_size_min or 50
        if 0 < emp < min_emp:
            negatives.append(Signal(
                account_id=account.id,
                signal_type="too_small",
                description=f"Company size ({emp}) is below ICP minimum ({min_emp}).",
                strength=1.0,
                source="Internal CRM",
                detected_at=now,
                confidence=1.0,
                evidence=f"employee_count={emp}"
            ))

        # 2. Wrong industry
        acc_ind = (account.industry or "").strip().lower()
        icp_inds = [i.strip().lower() for i in (icp.industries or [])]
        if acc_ind and acc_ind not in icp_inds and not any(kw in acc_ind for kw in ["software", "saas", "tech", "cloud"]):
            negatives.append(Signal(
                account_id=account.id,
                signal_type="wrong_industry",
                description=f"Industry '{account.industry}' does not match ICP.",
                strength=1.0,
                source="Internal CRM",
                detected_at=now,
                confidence=1.0,
                evidence=f"industry={account.industry}"
            ))

        # 3. Wrong geography
        acc_geo = (account.country or "").strip().lower()
        icp_geos = [g.strip().lower() for g in (icp.geographies or [])]
        if acc_geo and not any(g in acc_geo or acc_geo in g for g in icp_geos) and acc_geo not in ["us", "united states", "usa", "ca", "canada", "uk", "united kingdom", "gb"]:
            negatives.append(Signal(
                account_id=account.id,
                signal_type="wrong_geography",
                description=f"Country '{account.country}' is outside target ICP regions.",
                strength=1.0,
                source="Internal CRM",
                detected_at=now,
                confidence=1.0,
                evidence=f"country={account.country}"
            ))
            
        # 4. No use case (from exclusion criteria)
        desc = (account.description or "").lower()
        exclusions = [ex.lower() for ex in (icp.exclusions or [])]
        for ex in exclusions:
            if ex in acc_ind or ex in desc:
                negatives.append(Signal(
                    account_id=account.id,
                    signal_type="no_use_case",
                    description=f"Matched exclusion criterion: '{ex}'",
                    strength=1.0,
                    source="Internal CRM",
                    detected_at=now,
                    confidence=1.0,
                    evidence=f"description matched {ex}"
                ))
                break

        # Remove existing deterministically generated negative signals to replace them
        existing_negatives = db.query(Signal).filter(
            Signal.account_id == account.id,
            Signal.source == "Internal CRM"
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
        
        # Deduplicate signals of the same type (keep most recent)
        best_signals = {}
        for sig in signals:
            if sig.signal_type not in best_signals:
                best_signals[sig.signal_type] = sig
            elif sig.detected_at and best_signals[sig.signal_type].detected_at and sig.detected_at > best_signals[sig.signal_type].detected_at:
                best_signals[sig.signal_type] = sig
                
        now = datetime.utcnow()
        raw_score = 0.0
        
        for sig in best_signals.values():
            weight = SIGNAL_WEIGHTS.get(sig.signal_type, 0.0)
            if weight == 0.0:
                continue
                
            # Recency decay
            days_old = (now - sig.detected_at).days if sig.detected_at else 0
            decay = 1.0
            if days_old > 180:
                decay = 0.0
            elif days_old > 90:
                decay = 0.5
                
            # Base strength and confidence
            strength = sig.strength if sig.strength is not None else 1.0
            confidence = sig.confidence if sig.confidence is not None else 1.0
            
            signal_score = weight * strength * confidence * decay
            raw_score += signal_score
            
        # Scale the score out of 20
        return min(20.0, max(0.0, raw_score))
