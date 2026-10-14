"""
tests/test_recommendation.py
Table-driven unit tests for the deterministic RecommendationEngine.
"""
import pytest
from app.models import Score, Signal, ICPProfile
from app.services.recommendation_engine import RecommendationEngine, SIGNAL_TO_ANGLE

@pytest.fixture
def engine():
    return RecommendationEngine()

@pytest.fixture
def default_icp():
    return ICPProfile(
        buyer_roles=[
            "VP of Customer Support",
            "Head of Customer Experience",
            "Chief Revenue Officer",
            "Head of Product",
            "VP Operations"
        ]
    )

# ──────────────────────────────────────────────────────────────────────────────
# 1. Action Matrix Table-Driven Tests
# ──────────────────────────────────────────────────────────────────────────────

ACTION_TEST_CASES = [
    # (tier, intent_score, expected_action, expected_reason_substring)
    ("Priority 1", 20.0, "CONTACT", "strong intent signals"),
    ("Priority 1", 10.0, "CONTACT", "strong intent signals"),
    ("Priority 1", 9.9,  "RESEARCH", "lacking strong intent"),
    ("Priority 1", 0.0,  "RESEARCH", "lacking strong intent"),
    ("Priority 2", 20.0, "PRIORITIZE", "very high intent"),
    ("Priority 2", 15.0, "PRIORITIZE", "very high intent"),
    ("Priority 2", 14.9, "NURTURE", "moderate intent"),
    ("Priority 2", 5.0,  "NURTURE", "moderate intent"),
    ("Priority 2", 4.9,  "RESEARCH", "weak intent"),
    ("Priority 2", 0.0,  "RESEARCH", "weak intent"),
    ("Priority 3", 15.0, "NURTURE", "showing some buying signals"),
    ("Priority 3", 10.0, "NURTURE", "showing some buying signals"),
    ("Priority 3", 9.9,  "DEPRIORITIZE", "weak intent"),
    ("Priority 3", 0.0,  "DEPRIORITIZE", "weak intent"),
    ("Low",        20.0, "DEPRIORITIZE", "Low fit account"),
    ("Low",        5.0,  "DEPRIORITIZE", "Low fit account"),
    ("Low",        0.0,  "DEPRIORITIZE", "Low fit account"),
]

@pytest.mark.parametrize("tier,intent_score,expected_action,expected_reason_sub", ACTION_TEST_CASES)
def test_action_matrix_rules(engine, default_icp, tier, intent_score, expected_action, expected_reason_sub):
    score = Score(tier=tier, intent_score=intent_score, total_score=80.0)
    rec = engine.get_recommendation(score, [], default_icp)
    
    assert rec.action == expected_action
    assert expected_reason_sub.lower() in rec.reason.lower()

# ──────────────────────────────────────────────────────────────────────────────
# 2. Persona and Angle Mapping Tests
# ──────────────────────────────────────────────────────────────────────────────

SIGNAL_MAPPING_TEST_CASES = [
    # (signal_type, expected_angle_sub, expected_persona_sub)
    ("support_hiring", "support team scaling", "Support"),
    ("funding", "post-funding growth", "Revenue"),
    ("product_launch", "supporting new product", "Product"),
    ("international_expansion", "managing global operations", "VP of Customer Support"),
    ("relevant_technology", "integrating with your existing tech stack", "Product"),
    ("rapid_growth", "handling increased volume", "Revenue"),
    ("executive_change", "new strategic initiatives", "VP of Customer Support"),
]

@pytest.mark.parametrize("signal_type,expected_angle_sub,expected_persona_sub", SIGNAL_MAPPING_TEST_CASES)
def test_persona_and_angle_mapping(engine, default_icp, signal_type, expected_angle_sub, expected_persona_sub):
    score = Score(tier="Priority 1", intent_score=15.0)
    sig = Signal(signal_type=signal_type, strength=0.9, source="News")
    
    rec = engine.get_recommendation(score, [sig], default_icp)
    assert expected_angle_sub.lower() in rec.suggested_angle.lower()
    assert expected_persona_sub.lower() in rec.suggested_persona.lower()

def test_multiple_signals_picks_strongest(engine, default_icp):
    score = Score(tier="Priority 1", intent_score=15.0)
    sig_weak = Signal(signal_type="support_hiring", strength=0.3)
    sig_strong = Signal(signal_type="funding", strength=0.95)
    
    rec = engine.get_recommendation(score, [sig_weak, sig_strong], default_icp)
    assert rec.suggested_angle == SIGNAL_TO_ANGLE["funding"]
    assert "Revenue" in rec.suggested_persona

# ──────────────────────────────────────────────────────────────────────────────
# 3. Determinism Test
# ──────────────────────────────────────────────────────────────────────────────

def test_recommendation_determinism(engine, default_icp):
    score = Score(tier="Priority 2", intent_score=16.0)
    sig = Signal(signal_type="support_hiring", strength=0.85)

    rec1 = engine.get_recommendation(score, [sig], default_icp)
    rec2 = engine.get_recommendation(score, [sig], default_icp)

    assert rec1.action == rec2.action
    assert rec1.reason == rec2.reason
    assert rec1.suggested_persona == rec2.suggested_persona
    assert rec1.suggested_angle == rec2.suggested_angle
