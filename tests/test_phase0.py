import pytest
from sqlalchemy import inspect
from pydantic import BaseModel
from app.db.database import engine
from app.db.init_db import init_db
from app.api.main import app
from app.ai.llm import LLMService
from fastapi.testclient import TestClient


class DummySchema(BaseModel):
    title: str
    score: float
    is_active: bool


def test_database_tables_exist():
    # Initialize DB tables
    init_db()
    
    # Inspect tables using SQLAlchemy inspect
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    expected_tables = {
        "products",
        "icp_profiles",
        "accounts",
        "signals",
        "scores",
        "contacts",
        "activities",
        "opportunities",
        "drafts",
    }
    
    assert expected_tables.issubset(existing_tables), f"Missing tables: {expected_tables - existing_tables}"


def test_api_health_endpoint():
    init_db()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_llm_service_mock_mode():
    llm = LLMService(mode="mock")
    res = llm.generate_structured("Extract product info", DummySchema)
    assert isinstance(res, DummySchema)
    assert isinstance(res.title, str)
    assert isinstance(res.score, float)
    assert isinstance(res.is_active, bool)


def test_llm_service_live_mode_no_api_key():
    llm = LLMService(mode="live", api_key="")
    with pytest.raises(ValueError, match="LLM_API_KEY is not set"):
        llm.generate_structured("Test prompt", DummySchema)
