import pytest
from fastapi.testclient import TestClient
from app.api.main import app
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Product, Account, ICPProfile, Score
from app.services.icp_engine import ICPEngine
from app.services.research_engine import ResearchEngine
from app.services.scoring_engine import ScoringEngine
from app.schemas.icp import ICPProfileSchema

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_icp_engine_generation(db_session):
    product = Product(
        name="Support AI Agent",
        description="Autonomous customer support ticket resolution platform for B2B SaaS.",
        target_market=["B2B SaaS"],
        geography=["US"],
        price_range="$20k"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    engine = ICPEngine()
    icp = engine.generate_icp_for_product(db_session, product)

    assert icp.id is not None
    assert icp.product_id == product.id
    assert isinstance(icp.industries, list)
    assert icp.company_size_min == 50
    assert icp.company_size_max == 500
    assert "US" in icp.geographies


def test_research_engine_csv_ingestion(db_session):
    re = ResearchEngine()
    count = re.load_accounts_from_csv(db_session)
    assert count >= 150

    acme = db_session.query(Account).filter_by(name="Acme Technologies").first()
    assert acme is not None
    assert acme.domain == "acme.com"
    assert acme.employee_count == 240
    assert acme.industry == "B2B SaaS"


def test_scoring_engine_acme(db_session):
    product = db_session.query(Product).first()
    if not product:
        product = Product(
            name="Support AI Agent",
            description="Autonomous customer support ticket resolution platform for B2B SaaS.",
            target_market=["B2B SaaS"],
            geography=["US"],
            price_range="$20k"
        )
        db_session.add(product)
        db_session.commit()

    icp_engine = ICPEngine()
    icp_engine.generate_icp_for_product(db_session, product)

    acme = db_session.query(Account).filter_by(name="Acme Technologies").first()
    assert acme is not None

    se = ScoringEngine()
    result = se.score_account(db_session, acme, product)

    assert result.total_score >= 75.0  # Acme is a high-fit account (Tier 1/2)
    assert result.tier in ["Priority 1", "Priority 2"]
    assert result.icp_fit == 30.0
    assert result.company_fit == 20.0
    assert result.geography_score == 15.0


def test_api_endpoints():
    client = TestClient(app)

    # 1. POST /products
    prod_resp = client.post("/products", json={
        "name": "Test Product API",
        "description": "API Test platform for SaaS customer support.",
        "target_market": ["B2B SaaS"],
        "geography": ["US"],
        "price_range": "$15,000"
    })
    assert prod_resp.status_code == 200
    prod_data = prod_resp.json()
    product_id = prod_data["id"]

    # 2. POST /products/{id}/generate-icp
    icp_resp = client.post(f"/products/{product_id}/generate-icp")
    assert icp_resp.status_code == 200
    icp_data = icp_resp.json()
    assert icp_data["product_id"] == product_id
    assert icp_data["company_size_min"] == 50

    # 3. GET /accounts
    accs_resp = client.get("/accounts")
    assert accs_resp.status_code == 200
    accs_data = accs_resp.json()
    assert len(accs_data) >= 150
    first_acc_id = accs_data[0]["id"]

    # 4. GET /accounts/{id}
    acc_detail_resp = client.get(f"/accounts/{first_acc_id}")
    assert acc_detail_resp.status_code == 200
    assert acc_detail_resp.json()["id"] == first_acc_id

    # 5. POST /accounts/{id}/score?product_id={product_id}
    score_resp = client.post(f"/accounts/{first_acc_id}/score?product_id={product_id}")
    assert score_resp.status_code == 200
    score_data = score_resp.json()
    assert "total_score" in score_data
    assert "tier" in score_data

    # 6. POST /products/{id}/score-all
    batch_resp = client.post(f"/products/{product_id}/score-all")
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert len(batch_data) >= 150
