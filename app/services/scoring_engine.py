from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Account, Product, ICPProfile, Score
from app.schemas.scoring import ScoreResult, ComponentScore, ScoreReason


@dataclass
class ICPData:
    """Pure-Python ICP data carrier used by compute_score – no DB dependency."""
    industries: List[str] = field(default_factory=list)
    company_size_min: int = 50
    company_size_max: int = 500
    geographies: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)


@dataclass
class AccountData:
    """Pure-Python account data carrier used by compute_score – no DB dependency."""
    id: int = 0
    industry: Optional[str] = None
    description: Optional[str] = None
    employee_count: Optional[int] = None
    country: Optional[str] = None
    technology_stack: Optional[List[str]] = None
    support_team_size: Optional[int] = None
    funding: Optional[str] = None
    intent_score_override: Optional[float] = None


def _tier(total: float) -> str:
    if total >= 90.0:
        return "Priority 1"
    elif total >= 75.0:
        return "Priority 2"
    elif total >= 50.0:
        return "Priority 3"
    return "Low"


class ScoringEngine:
    """
    Deterministic scoring engine that evaluates target accounts against an ICP profile.
    Total maximum score: 100 points.
    compute_score() is pure: no DB, no LLM, always deterministic.
    score_account() wraps compute_score() with DB persistence.
    """

    # ------------------------------------------------------------------ #
    # Pure computation – no DB, no LLM                                    #
    # ------------------------------------------------------------------ #

    def _intent(self, account: AccountData) -> Tuple[float, List[ScoreReason]]:
        """Proxy intent score /20 from support team size and funding stage."""
        reasons: List[ScoreReason] = []
        supp_size = account.support_team_size or 0

        if supp_size >= 15:
            s_pts = 12.0
        elif supp_size >= 5:
            s_pts = 6.0
        else:
            s_pts = 2.0
        reasons.append(ScoreReason(
            rule="Support Team Size",
            met=supp_size >= 5,
            text=f"Support team size ({supp_size}): {'meets' if supp_size >= 5 else 'below'} threshold.",
            points=s_pts
        ))

        funding = (account.funding or "").strip()
        high_funding = ["series b", "series c", "growth", "public"]
        mid_funding = ["series a", "seed"]
        fl = funding.lower()

        if any(f in fl for f in high_funding):
            f_pts = 8.0
        elif any(f in fl for f in mid_funding):
            f_pts = 5.0
        else:
            f_pts = 2.0
        reasons.append(ScoreReason(
            rule="Funding Stage",
            met=f_pts >= 5.0,
            text=f"Funding stage '{funding}' gives {f_pts} intent points.",
            points=f_pts
        ))

        return min(20.0, s_pts + f_pts), reasons

    def compute_score(self, account: AccountData, icp: ICPData, product_id: int = 0) -> ScoreResult:
        """
        Pure deterministic computation. No DB calls. Always gives the same output
        for the same input.
        """
        reasons: List[ScoreReason] = []

        # ── 1. ICP Fit /30 ───────────────────────────────────────────────
        acc_industry = (account.industry or "").strip().lower()
        icp_industries = [i.strip().lower() for i in icp.industries]
        adjacent_keywords = ["software", "saas", "tech", "cloud"]

        if acc_industry in icp_industries:
            ind_pts = 20.0
            reasons.append(ScoreReason(rule="Industry Match", met=True,
                text=f"Industry '{account.industry}' exactly matches ICP.", points=20.0))
        elif any(kw in acc_industry or acc_industry in kw for kw in adjacent_keywords):
            ind_pts = 10.0
            reasons.append(ScoreReason(rule="Industry Match", met=True,
                text=f"Industry '{account.industry}' is adjacent to ICP.", points=10.0))
        else:
            ind_pts = 0.0
            reasons.append(ScoreReason(rule="Industry Match", met=False,
                text=f"Industry '{account.industry}' does not match ICP.", points=0.0))

        desc = (account.description or "").lower()
        matched_pains = []
        for pain in icp.pain_points:
            words = [w.lower() for w in pain.split() if len(w) > 3]
            if any(w in desc for w in words):
                matched_pains.append(pain)

        kw_pts = min(10.0, len(matched_pains) * 5.0)
        reasons.append(ScoreReason(
            rule="Pain Point Overlap", met=bool(matched_pains),
            text=f"Matched pain points: {matched_pains}" if matched_pains else "No pain point overlap.",
            points=kw_pts
        ))

        icp_fit = min(30.0, ind_pts + kw_pts)

        # ── 2. Company Fit /20 ───────────────────────────────────────────
        emp = account.employee_count or 0
        min_emp = icp.company_size_min
        max_emp = icp.company_size_max

        if min_emp <= emp <= max_emp:
            comp_pts = 20.0
            reasons.append(ScoreReason(rule="Company Size", met=True,
                text=f"Employees ({emp}) within range {min_emp}–{max_emp}.", points=20.0))
        elif (min_emp * 0.75 <= emp < min_emp) or (max_emp < emp <= max_emp * 1.25):
            comp_pts = 10.0
            reasons.append(ScoreReason(rule="Company Size", met=True,
                text=f"Employees ({emp}) within 25% of range {min_emp}–{max_emp}.", points=10.0))
        else:
            comp_pts = 0.0
            reasons.append(ScoreReason(rule="Company Size", met=False,
                text=f"Employees ({emp}) outside range {min_emp}–{max_emp}.", points=0.0))

        # Exclusion penalty
        exclusions_lower = [ex.lower() for ex in icp.exclusions]
        for ex in exclusions_lower:
            if ex in acc_industry or ex in desc:
                comp_pts = max(0.0, comp_pts - 20.0)
                reasons.append(ScoreReason(rule="Exclusion Criterion", met=False,
                    text=f"Disqualifying exclusion matched: '{ex}'.", points=-20.0))
                break

        company_fit = min(20.0, max(0.0, comp_pts))

        # ── 3. Technology Fit /15 ────────────────────────────────────────
        acc_techs = [t.lower() for t in (account.technology_stack or [])]
        icp_techs = [t.lower() for t in icp.technologies]

        if icp_techs:
            overlap = [t for t in acc_techs if any(it in t or t in it for it in icp_techs)]
            if overlap:
                tech_pts = min(15.0, (len(overlap) / max(1, len(icp_techs))) * 15.0 * 1.5)
            else:
                tech_pts = 0.0
            reasons.append(ScoreReason(rule="Technology Stack", met=bool(overlap),
                text=f"Matching techs: {overlap}" if overlap else "No tech overlap.",
                points=round(tech_pts, 1)))
        else:
            tech_pts = 10.0
            reasons.append(ScoreReason(rule="Technology Stack", met=True,
                text="No specific tech requirements in ICP.", points=10.0))

        technology_fit = min(15.0, round(tech_pts, 1))

        # ── 4. Buying Intent /20 ─────────────────────────────────────────
        if account.intent_score_override is not None:
            intent_score = account.intent_score_override
            reasons.append(ScoreReason(
                rule="Signal Engine Intent", 
                met=True, 
                text=f"Intent score {intent_score:.1f} calculated from detected signals.", 
                points=intent_score
            ))
        else:
            intent_score, intent_reasons = self._intent(account)
            reasons.extend(intent_reasons)

        # ── 5. Geography Fit /15 ─────────────────────────────────────────
        acc_country = (account.country or "").strip().lower()
        icp_geos = [g.strip().lower() for g in icp.geographies]

        if any(acc_country == g or acc_country in g or g in acc_country for g in icp_geos):
            geo_pts = 15.0
            reasons.append(ScoreReason(rule="Geography Match", met=True,
                text=f"Country '{account.country}' matches target geographies.", points=15.0))
        elif acc_country in ["us", "united states", "usa", "ca", "canada",
                              "uk", "united kingdom", "gb"]:
            geo_pts = 8.0
            reasons.append(ScoreReason(rule="Geography Match", met=True,
                text=f"Country '{account.country}' is in target region.", points=8.0))
        else:
            geo_pts = 0.0
            reasons.append(ScoreReason(rule="Geography Match", met=False,
                text=f"Country '{account.country}' is outside target geographies.", points=0.0))

        geography_score = min(15.0, geo_pts)

        # ── Total & Tier ─────────────────────────────────────────────────
        raw_total = icp_fit + company_fit + technology_fit + intent_score + geography_score
        total_score = min(100.0, max(0.0, round(raw_total, 1)))
        tier = _tier(total_score)

        components = [
            ComponentScore(component="ICP Fit",          score=icp_fit,          max_score=30.0),
            ComponentScore(component="Company Fit",       score=company_fit,       max_score=20.0),
            ComponentScore(component="Technology Fit",    score=technology_fit,    max_score=15.0),
            ComponentScore(component="Buying Intent",     score=intent_score,      max_score=20.0),
            ComponentScore(component="Geography Fit",     score=geography_score,   max_score=15.0),
        ]

        return ScoreResult(
            account_id=account.id,
            product_id=product_id,
            total_score=total_score,
            tier=tier,
            icp_fit=icp_fit,
            company_fit=company_fit,
            technology_fit=technology_fit,
            intent_score=intent_score,
            geography_score=geography_score,
            components=components,
            reasons=reasons,
        )

    # ------------------------------------------------------------------ #
    # DB-backed wrapper                                                    #
    # ------------------------------------------------------------------ #

    def score_account(self, db: Session, account: Account, product: Product) -> ScoreResult:
        """Loads ICP from DB, delegates to compute_score, persists result."""
        db_icp: ICPProfile = db.query(ICPProfile).filter_by(product_id=product.id).first()
        if not db_icp:
            raise ValueError(f"No ICP Profile for product {product.id}. Generate ICP first.")

        icp = ICPData(
            industries=db_icp.industries or [],
            company_size_min=db_icp.company_size_min or 50,
            company_size_max=db_icp.company_size_max or 500,
            geographies=db_icp.geographies or [],
            pain_points=db_icp.pain_points or [],
            technologies=db_icp.technologies or [],
            exclusions=db_icp.exclusions or [],
        )
        from app.services.signal_engine import SignalEngine
        signal_engine = SignalEngine()
        calculated_intent = signal_engine.calculate_intent(db, account, product)

        acc = AccountData(
            id=account.id,
            industry=account.industry,
            description=account.description,
            employee_count=account.employee_count,
            country=account.country,
            technology_stack=account.technology_stack,
            support_team_size=account.support_team_size,
            funding=account.funding,
            intent_score_override=calculated_intent,
        )

        result = self.compute_score(acc, icp, product_id=product.id)

        reasoning_data = {
            "components": [c.model_dump() for c in result.components],
            "reasons":    [r.model_dump() for r in result.reasons],
        }

        existing = db.query(Score).filter_by(
            account_id=account.id, product_id=product.id
        ).first()

        if existing:
            existing.icp_fit         = result.icp_fit
            existing.company_fit     = result.company_fit
            existing.technology_fit  = result.technology_fit
            existing.intent_score    = result.intent_score
            existing.geography_score = result.geography_score
            existing.total_score     = result.total_score
            existing.tier            = result.tier
            existing.reasoning       = reasoning_data
        else:
            db.add(Score(
                account_id=account.id,
                product_id=product.id,
                icp_fit=result.icp_fit,
                company_fit=result.company_fit,
                technology_fit=result.technology_fit,
                intent_score=result.intent_score,
                geography_score=result.geography_score,
                total_score=result.total_score,
                tier=result.tier,
                reasoning=reasoning_data,
            ))

        db.commit()
        return result
