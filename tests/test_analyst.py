"""
tests/test_analyst.py
Unit tests for AnalystService routing, execution, and explanation grounding.
Uses LLMService in mock mode (no real API calls).
"""
import json
import re
import pytest
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.analyst_service import AnalystService
from app.ai.llm import LLMService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="module")
def analyst():
    return AnalystService(llm=LLMService(mode="mock"))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def numbers_in(text: str):
    """Extract all numeric tokens from a string (int or float)."""
    return set(re.findall(r'\b\d+(?:[.,]\d+)?\b', text))


def all_data_numbers(data: dict) -> set:
    """Return all numeric tokens found anywhere in the JSON-serialized data."""
    return numbers_in(json.dumps(data))


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------

ROUTING_CASES = [
    # (question, expected_function)
    ("What are the conversion rates?", "get_conversion_rates"),
    ("Show me stage to stage drop off", "get_conversion_rates"),
    ("Show me weekly trends", "get_weekly_trends"),
    ("What is our timeline of activity?", "get_weekly_trends"),
    ("What is our tier performance?", "get_tier_performance"),
    ("Which industry performs best?", "get_industry_performance"),
    ("Which sector replies most?", "get_industry_performance"),
    ("What is our funnel summary?", "get_funnel_summary"),
    ("How many accounts do we have?", "get_funnel_summary"),
    ("Give me a pipeline overview", "get_funnel_summary"),
]


@pytest.mark.parametrize("question,expected_fn", ROUTING_CASES)
def test_routing(db, analyst, question, expected_fn):
    result = analyst.ask(db, question)
    assert result.function_called == expected_fn, (
        f"Q: '{question}' -> got '{result.function_called}', expected '{expected_fn}'"
    )


# ---------------------------------------------------------------------------
# Data presence tests
# ---------------------------------------------------------------------------

def test_conversion_rates_data_has_conversions_key(db, analyst):
    result = analyst.ask(db, "What are the conversion rates?")
    assert "conversions" in result.data


def test_weekly_trends_data_has_weekly_trends_key(db, analyst):
    result = analyst.ask(db, "Show me weekly trends")
    assert "weekly_trends" in result.data


def test_tier_performance_data_has_tier_key(db, analyst):
    result = analyst.ask(db, "What is our tier performance?")
    assert "performance_by_tier" in result.data


def test_industry_performance_data_has_industry_key(db, analyst):
    result = analyst.ask(db, "Which industry performs best?")
    assert "performance_by_industry" in result.data


def test_funnel_summary_data_has_totals_key(db, analyst):
    result = analyst.ask(db, "Give me a funnel summary")
    assert "totals" in result.data or "stage_counts" in result.data


# ---------------------------------------------------------------------------
# Unmappable question
# ---------------------------------------------------------------------------

def test_unmappable_question_returns_unknown(db, analyst):
    result = analyst.ask(db, "What is the weather in New York?")
    assert result.function_called == "unknown"


def test_unmappable_explanation_mentions_cannot(db, analyst):
    result = analyst.ask(db, "What is the weather in New York?")
    assert "cannot" in result.explanation.lower() or "map" in result.explanation.lower(), (
        f"Expected 'cannot' or 'map' in explanation, got: {result.explanation!r}"
    )


def test_unmappable_returns_empty_data(db, analyst):
    result = analyst.ask(db, "What is the weather in New York?")
    assert result.data == {}


# ---------------------------------------------------------------------------
# Explanation grounding: numbers in explanation must appear in data
# ---------------------------------------------------------------------------

def test_explanation_numbers_present_in_data_conversions(db, analyst):
    result = analyst.ask(db, "What are the conversion rates?")
    _assert_explanation_grounded(result)


def test_explanation_numbers_present_in_data_weekly(db, analyst):
    result = analyst.ask(db, "Show me weekly trends")
    _assert_explanation_grounded(result)


def test_explanation_numbers_present_in_data_funnel(db, analyst):
    result = analyst.ask(db, "Give me a funnel summary")
    _assert_explanation_grounded(result)


def _assert_explanation_grounded(result):
    """
    Every numeric token in the explanation must be present somewhere in
    the JSON-serialized data. This ensures the LLM did not invent figures.
    Skipped for unknown responses (no data to ground against).
    """
    if result.function_called == "unknown":
        return

    explanation_nums = numbers_in(result.explanation)
    data_nums = all_data_numbers(result.data)

    for num in explanation_nums:
        assert num in data_nums, (
            f"Number '{num}' in explanation not found in data.\n"
            f"Explanation: {result.explanation!r}\n"
            f"Data numbers: {sorted(data_nums)}"
        )


# ---------------------------------------------------------------------------
# Determinism: same input -> same output
# ---------------------------------------------------------------------------

def test_same_question_gives_same_function(db, analyst):
    q = "What are the conversion rates?"
    r1 = analyst.ask(db, q)
    r2 = analyst.ask(db, q)
    assert r1.function_called == r2.function_called


# ---------------------------------------------------------------------------
# Question field is echoed back
# ---------------------------------------------------------------------------

def test_question_echoed_back(db, analyst):
    q = "What is our tier performance?"
    result = analyst.ask(db, q)
    assert result.question == q
