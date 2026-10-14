"""
tests/test_scoring.py
Pure unit tests – no DB, no LLM.
All tests call ScoringEngine.compute_score(AccountData, ICPData) directly.
"""
import pytest
from app.services.scoring_engine import ScoringEngine, AccountData, ICPData

ENGINE = ScoringEngine()

PERFECT_ICP = ICPData(
    industries=["b2b saas"],
    company_size_min=50,
    company_size_max=500,
    geographies=["us"],
    pain_points=["high support ticket volume", "help desk overload"],
    technologies=["zendesk", "salesforce"],
    exclusions=[],
)


def _acct(**kwargs) -> AccountData:
    defaults = dict(
        id=1,
        industry="B2B SaaS",
        description="Platform facing high support ticket volume and help desk overload.",
        employee_count=200,
        country="US",
        technology_stack=["Zendesk", "Salesforce"],
        support_team_size=20,
        funding="Series B",
    )
    defaults.update(kwargs)
    return AccountData(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Perfect account
# ──────────────────────────────────────────────────────────────────────────────

def test_perfect_account_scores_100():
    result = ENGINE.compute_score(_acct(), PERFECT_ICP)
    # ICP: 20+10=30, Company: 20, Tech: 15 (2/2*1.5*15=min(15,22.5)=15),
    # Intent: 12+8=20, Geo: 15  → 100
    assert result.total_score == 100.0
    assert result.tier == "Priority 1"


# ──────────────────────────────────────────────────────────────────────────────
# 2. Wrong industry / size / country all together
# ──────────────────────────────────────────────────────────────────────────────

def test_bad_fit_scores_low():
    bad = _acct(
        industry="Hardware Manufacturing",
        description="Makes industrial sensors.",
        employee_count=5000,
        country="Brazil",
        technology_stack=["Oracle"],
        support_team_size=2,
        funding="Bootstrapped",
    )
    result = ENGINE.compute_score(bad, PERFECT_ICP)
    assert result.total_score < 50.0
    assert result.tier == "Low"


# ──────────────────────────────────────────────────────────────────────────────
# 3. Size boundaries
# ──────────────────────────────────────────────────────────────────────────────

def test_size_exactly_min_scores_full_company_fit():
    result = ENGINE.compute_score(_acct(employee_count=50), PERFECT_ICP)
    assert result.company_fit == 20.0

def test_size_exactly_max_scores_full_company_fit():
    result = ENGINE.compute_score(_acct(employee_count=500), PERFECT_ICP)
    assert result.company_fit == 20.0

def test_size_just_below_min_within_25pct_scores_partial():
    # min=50, 25% boundary = 37. emp=38 → partial
    result = ENGINE.compute_score(_acct(employee_count=38), PERFECT_ICP)
    assert result.company_fit == 10.0

def test_size_just_above_max_within_25pct_scores_partial():
    # max=500, 25% boundary = 625. emp=624 → partial
    result = ENGINE.compute_score(_acct(employee_count=624), PERFECT_ICP)
    assert result.company_fit == 10.0

def test_size_far_below_min_scores_zero_company_fit():
    result = ENGINE.compute_score(_acct(employee_count=5), PERFECT_ICP)
    assert result.company_fit == 0.0

def test_size_far_above_max_scores_zero_company_fit():
    result = ENGINE.compute_score(_acct(employee_count=2000), PERFECT_ICP)
    assert result.company_fit == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# 4. Tier boundaries
# ──────────────────────────────────────────────────────────────────────────────

def _score_with_total(total: float) -> str:
    """Force a specific total by adjusting employee count to get 0 company fit,
    then use the exact value via direct call to _tier."""
    from app.services.scoring_engine import _tier
    return _tier(total)

def test_tier_boundary_49():   assert _score_with_total(49.0) == "Low"
def test_tier_boundary_50():   assert _score_with_total(50.0) == "Priority 3"
def test_tier_boundary_74():   assert _score_with_total(74.0) == "Priority 3"
def test_tier_boundary_75():   assert _score_with_total(75.0) == "Priority 2"
def test_tier_boundary_89():   assert _score_with_total(89.0) == "Priority 2"
def test_tier_boundary_90():   assert _score_with_total(90.0) == "Priority 1"


# ──────────────────────────────────────────────────────────────────────────────
# 5. Exclusion criteria reduce company_fit to 0
# ──────────────────────────────────────────────────────────────────────────────

def test_exclusion_criterion_zeroes_company_fit():
    icp_with_excl = ICPData(
        industries=["b2b saas"],
        company_size_min=50,
        company_size_max=500,
        geographies=["us"],
        pain_points=[],
        technologies=[],
        exclusions=["B2C Only"],
    )
    bad_acc = _acct(industry="B2C Only", description="B2C consumer platform")
    result = ENGINE.compute_score(bad_acc, icp_with_excl)
    assert result.company_fit == 0.0
    exclusion_reasons = [r for r in result.reasons if r.rule == "Exclusion Criterion"]
    assert len(exclusion_reasons) == 1
    assert not exclusion_reasons[0].met


def test_exclusion_in_description_zeroes_company_fit():
    icp_with_excl = ICPData(
        industries=["b2b saas"],
        company_size_min=50,
        company_size_max=500,
        geographies=["us"],
        pain_points=[],
        technologies=[],
        exclusions=["government"],
    )
    gov_acc = _acct(industry="B2B SaaS", description="Government public sector platform")
    result = ENGINE.compute_score(gov_acc, icp_with_excl)
    assert result.company_fit == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# 6. No component exceeds its maximum; total == sum of components
# ──────────────────────────────────────────────────────────────────────────────

MAXES = {"ICP Fit": 30.0, "Company Fit": 20.0,
          "Technology Fit": 15.0, "Buying Intent": 20.0, "Geography Fit": 15.0}

@pytest.mark.parametrize("acct,icp", [
    (_acct(), PERFECT_ICP),
    (_acct(industry="Retail", country="Japan", employee_count=1, funding="Bootstrapped"), PERFECT_ICP),
    (_acct(technology_stack=[], support_team_size=0, funding=""), PERFECT_ICP),
])
def test_components_within_max_and_sum_to_total(acct, icp):
    result = ENGINE.compute_score(acct, icp)
    for c in result.components:
        assert c.score <= c.max_score, f"{c.component} ({c.score}) exceeds max ({c.max_score})"
        assert c.score >= 0.0, f"{c.component} is negative"
    component_sum = round(sum(c.score for c in result.components), 1)
    assert result.total_score == component_sum


# ──────────────────────────────────────────────────────────────────────────────
# 7. Determinism – same input always same output
# ──────────────────────────────────────────────────────────────────────────────

def test_deterministic():
    a = _acct(employee_count=150, funding="Series A", support_team_size=8)
    r1 = ENGINE.compute_score(a, PERFECT_ICP)
    r2 = ENGINE.compute_score(a, PERFECT_ICP)
    r3 = ENGINE.compute_score(a, PERFECT_ICP)
    assert r1.total_score == r2.total_score == r3.total_score
    assert r1.tier == r2.tier == r3.tier
