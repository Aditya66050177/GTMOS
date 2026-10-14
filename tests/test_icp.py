"""
tests/test_icp.py
Tests for ICP generation, LLM validation, retry logic, and DB persistence.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Product, ICPProfile
from app.schemas.icp import ICPProfileSchema
from app.services.icp_engine import ICPEngine
from app.ai.llm import LLMService


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_product(db, suffix="") -> Product:
    p = Product(
        name=f"ICP Test Product{suffix}",
        description="AI customer support automation platform.",
        target_market=["B2B SaaS"],
        geography=["US"],
        price_range="$20k",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ──────────────────────────────────────────────────────────────────────────────
# 1. Mock ICP output validates against ICPProfileSchema
# ──────────────────────────────────────────────────────────────────────────────

def test_mock_icp_validates_against_schema():
    llm = LLMService(mode="mock")
    result = llm.generate_structured("Generate ICP", ICPProfileSchema)
    assert isinstance(result, ICPProfileSchema)
    assert len(result.industries) > 0
    assert result.min_employees == 50
    assert result.max_employees == 500
    assert "US" in result.geographies
    assert len(result.pain_points) > 0
    assert len(result.technologies) > 0
    assert len(result.exclusion_criteria) > 0


# ──────────────────────────────────────────────────────────────────────────────
# 2. Invalid LLM JSON is rejected and retried exactly once
# ──────────────────────────────────────────────────────────────────────────────

def test_invalid_json_triggers_one_retry():
    """
    In live mode, if _call_live_provider returns invalid JSON both times,
    it retries once and then raises RuntimeError after 2 attempts.
    """
    llm = LLMService(mode="live", api_key="fake-key-for-test")
    call_count = 0

    def bad_provider(prompt, schema):
        nonlocal call_count
        call_count += 1
        return "this is not valid json {"   # always broken

    with patch.object(llm, "_call_live_provider", side_effect=bad_provider):
        with pytest.raises(RuntimeError, match="Failed to generate valid Pydantic response"):
            llm.generate_structured("test", ICPProfileSchema)

    assert call_count == 2  # tried exactly twice


def test_invalid_schema_triggers_one_retry():
    """
    If the JSON is valid but doesn't match the schema, also retried once.
    """
    llm = LLMService(mode="live", api_key="fake-key-for-test")
    call_count = 0

    def wrong_schema_provider(prompt, schema):
        nonlocal call_count
        call_count += 1
        return json.dumps({"wrong_key": "wrong_value"})

    with patch.object(llm, "_call_live_provider", side_effect=wrong_schema_provider):
        with pytest.raises(RuntimeError):
            llm.generate_structured("test", ICPProfileSchema)

    assert call_count == 2


def test_retry_succeeds_on_second_attempt():
    """
    First call returns invalid JSON; second call returns valid JSON.
    Should succeed without raising.
    """
    valid_payload = json.dumps({
        "industries": ["B2B SaaS"],
        "min_employees": 50,
        "max_employees": 500,
        "geographies": ["US"],
        "buyer_roles": ["VP Sales"],
        "pain_points": ["High ticket volume"],
        "technologies": ["Zendesk"],
        "buying_triggers": ["Funding"],
        "exclusion_criteria": ["B2C Only"],
    })

    llm = LLMService(mode="live", api_key="fake-key-for-test")
    calls = []

    def provider_that_succeeds_second(prompt, schema):
        calls.append(1)
        if len(calls) == 1:
            return "{ bad json"
        return valid_payload

    with patch.object(llm, "_call_live_provider", side_effect=provider_that_succeeds_second):
        result = llm.generate_structured("test", ICPProfileSchema)

    assert isinstance(result, ICPProfileSchema)
    assert len(calls) == 2


# ──────────────────────────────────────────────────────────────────────────────
# 3. ICP stored as structured columns and reads back correctly
# ──────────────────────────────────────────────────────────────────────────────

def test_icp_stored_as_structured_columns(db):
    product = _make_product(db, suffix=" Struct")
    engine = ICPEngine()
    icp = engine.generate_icp_for_product(db, product)

    assert icp.id is not None
    assert icp.product_id == product.id

    # Read back from DB
    stored = db.query(ICPProfile).filter_by(product_id=product.id).first()
    assert stored is not None

    # Stored as lists (JSON columns), not text blobs
    assert isinstance(stored.industries, list)
    assert isinstance(stored.geographies, list)
    assert isinstance(stored.pain_points, list)
    assert isinstance(stored.technologies, list)
    assert isinstance(stored.exclusions, list)
    assert isinstance(stored.buying_triggers, list)

    # Values match the mock fixture
    assert "B2B SaaS" in stored.industries
    assert stored.company_size_min == 50
    assert stored.company_size_max == 500


def test_icp_generation_is_idempotent(db):
    """Running generate_icp_for_product twice should update, not duplicate."""
    product = _make_product(db, suffix=" Idempotent")
    engine = ICPEngine()

    icp1 = engine.generate_icp_for_product(db, product)
    icp2 = engine.generate_icp_for_product(db, product)

    assert icp1.id == icp2.id
    count = db.query(ICPProfile).filter_by(product_id=product.id).count()
    assert count == 1
