from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.analytics import (
    FunnelAnalyticsResponse,
    TrendsAnalyticsResponse,
    AnalystAskRequest,
    AnalystAskResponse
)
from app.services.analytics_engine import AnalyticsEngine
from app.services.analyst_service import AnalystService

router = APIRouter(prefix="/analytics", tags=["GTM Analytics & AI Analyst"])

@router.get("/funnel", response_model=FunnelAnalyticsResponse)
def get_funnel_analytics(
    product_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    engine = AnalyticsEngine()
    return engine.get_funnel_analytics(db=db, product_id=product_id)

@router.get("/trends", response_model=TrendsAnalyticsResponse)
def get_trends_analytics(db: Session = Depends(get_db)):
    engine = AnalyticsEngine()
    return engine.get_weekly_trends(db=db)

@router.post("/ask", response_model=AnalystAskResponse)
def ask_analyst(payload: AnalystAskRequest, db: Session = Depends(get_db)):
    analyst = AnalystService()
    try:
        response = analyst.ask(db=db, question=payload.question)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing query: {str(e)}")
