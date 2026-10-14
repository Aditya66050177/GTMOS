from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models import Product, Account
from app.schemas.product import ProductCreate, ProductResponse
from app.schemas.scoring import ScoreResult
from app.services.icp_engine import ICPEngine
from app.services.scoring_engine import ScoringEngine
from app.services.research_engine import ResearchEngine

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("", response_model=ProductResponse)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    product = Product(
        name=product_in.name,
        description=product_in.description,
        target_market=product_in.target_market,
        geography=product_in.geography,
        price_range=product_in.price_range
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.get("", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@router.get("/{id}", response_model=ProductResponse)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter_by(id=id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {id} not found.")
    return product

@router.post("/{id}/generate-icp")
def generate_icp(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter_by(id=id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {id} not found.")
    engine = ICPEngine()
    icp_profile = engine.generate_icp_for_product(db, product)
    return {
        "product_id": product.id,
        "icp_profile_id": icp_profile.id,
        "industries": icp_profile.industries,
        "company_size_min": icp_profile.company_size_min,
        "company_size_max": icp_profile.company_size_max,
        "geographies": icp_profile.geographies,
        "buyer_roles": icp_profile.buyer_roles,
        "pain_points": icp_profile.pain_points,
        "technologies": icp_profile.technologies,
        "buying_triggers": icp_profile.buying_triggers,
        "exclusions": icp_profile.exclusions
    }

@router.post("/{id}/score-all", response_model=List[ScoreResult])
def score_all_accounts(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter_by(id=id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {id} not found.")

    accounts = db.query(Account).all()
    if not accounts:
        re = ResearchEngine()
        re.load_accounts_from_csv(db)
        accounts = db.query(Account).all()

    scoring_engine = ScoringEngine()
    results = []
    for acc in accounts:
        res = scoring_engine.score_account(db, acc, product)
        results.append(res)

    return results
