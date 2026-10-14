import pytest
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

from app.api.main import app
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import (
    Product,
    ICPProfile,
    Account,
    Signal,
    Score,
    Contact,
    Activity,
    Opportunity,
    Draft,
)
from app.ai.llm import LLMService


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


def test_models_insert_and_read_rollback(db_session):
    # 1. Product
    product = Product(
        name="Test Platform",
        description="GTM Automation Tool",
        target_market=["Enterprise", "SMB"],
        geography=["US", "EU"],
        price_range="$10k-$50k"
    )
    db_session.add(product)
    db_session.flush()
    assert product.id is not None

    read_product = db_session.query(Product).filter_by(id=product.id).first()
    assert read_product is not None
    assert read_product.name == "Test Platform"

    # 2. ICPProfile
    icp = ICPProfile(
        product_id=product.id,
        industries=["SaaS", "Fintech"],
        company_size_min=50,
        company_size_max=500,
        geographies=["US"],
        buyer_roles=["VP Sales", "CRO"],
        pain_points=["Low conversion"],
        technologies=["Salesforce"],
        buying_triggers=["Hiring SDRs"],
        exclusions=["B2C"]
    )
    db_session.add(icp)
    db_session.flush()
    assert icp.id is not None
    read_icp = db_session.query(ICPProfile).filter_by(id=icp.id).first()
    assert read_icp is not None

    # 3. Account
    account = Account(
        name="Acme Corp",
        domain="acme.com",
        industry="SaaS",
        employee_count=150,
        country="US",
        description="Leading SaaS vendor",
        technology_stack=["HubSpot", "AWS"],
        funding="Series B",
        support_team_size=10
    )
    db_session.add(account)
    db_session.flush()
    assert account.id is not None
    read_account = db_session.query(Account).filter_by(id=account.id).first()
    assert read_account is not None
    assert read_account.name == "Acme Corp"

    # 4. Signal
    signal = Signal(
        account_id=account.id,
        signal_type="Funding",
        description="Raised Series B",
        strength=0.9,
        source="TechCrunch",
        confidence=0.95,
        evidence={"url": "https://techcrunch.com/acme"}
    )
    db_session.add(signal)
    db_session.flush()
    assert signal.id is not None
    read_signal = db_session.query(Signal).filter_by(id=signal.id).first()
    assert read_signal is not None

    # 5. Score
    score = Score(
        account_id=account.id,
        product_id=product.id,
        icp_fit=85.0,
        company_fit=90.0,
        technology_fit=80.0,
        intent_score=75.0,
        geography_score=100.0,
        total_score=86.0,
        tier="Tier 1",
        reasoning={"fit_reasons": ["Size matches", "Tech matches"]}
    )
    db_session.add(score)
    db_session.flush()
    assert score.id is not None
    read_score = db_session.query(Score).filter_by(id=score.id).first()
    assert read_score is not None

    # 6. Contact
    contact = Contact(
        account_id=account.id,
        name="Jane Doe",
        role="VP of Sales",
        email="jane@acme.com",
        linkedin_url="https://linkedin.com/in/janedoe"
    )
    db_session.add(contact)
    db_session.flush()
    assert contact.id is not None
    read_contact = db_session.query(Contact).filter_by(id=contact.id).first()
    assert read_contact is not None

    # 7. Activity
    activity = Activity(
        account_id=account.id,
        contact_id=contact.id,
        activity_type="Email Sent",
        status="completed",
        activity_metadata={"template_id": 123}
    )
    db_session.add(activity)
    db_session.flush()
    assert activity.id is not None
    read_activity = db_session.query(Activity).filter_by(id=activity.id).first()
    assert read_activity is not None

    # 8. Opportunity
    opportunity = Opportunity(
        account_id=account.id,
        stage="Discovery",
        deal_value=25000.0,
        probability=0.3
    )
    db_session.add(opportunity)
    db_session.flush()
    assert opportunity.id is not None
    read_opp = db_session.query(Opportunity).filter_by(id=opportunity.id).first()
    assert read_opp is not None

    # 9. Draft
    draft = Draft(
        account_id=account.id,
        contact_id=contact.id,
        body="Hello Jane...",
        original_body="Hello Jane...",
        status="pending",
        evidence_ids=[signal.id]
    )
    db_session.add(draft)
    db_session.flush()
    assert draft.id is not None
    read_draft = db_session.query(Draft).filter_by(id=draft.id).first()
    assert read_draft is not None


def test_foreign_key_enforcement(db_session):
    invalid_signal = Signal(
        account_id=999999,
        signal_type="Hiring",
        description="Hiring VP Sales",
        strength=0.8,
        source="LinkedIn",
        confidence=0.9
    )
    db_session.add(invalid_signal)
    with pytest.raises(IntegrityError):
        db_session.flush()


class SampleSchema(BaseModel):
    summary: str
    relevance_score: float
    is_qualified: bool


def test_llm_service_mock_mode_validation():
    llm = LLMService(mode="mock")
    result = llm.generate_structured("Analyze account acme.com", SampleSchema)
    assert isinstance(result, SampleSchema)
    assert isinstance(result.summary, str)
    assert isinstance(result.relevance_score, float)
    assert isinstance(result.is_qualified, bool)


def test_llm_service_live_mode_no_api_key_error():
    llm = LLMService(mode="live", api_key="")
    with pytest.raises(ValueError, match="LLM_API_KEY is not set"):
        llm.generate_structured("Analyze account", SampleSchema)
