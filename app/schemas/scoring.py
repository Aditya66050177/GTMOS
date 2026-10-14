from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ComponentScore(BaseModel):
    component: str
    score: float
    max_score: float

class ScoreReason(BaseModel):
    rule: str
    met: bool
    text: str
    points: float

class ScoreResult(BaseModel):
    account_id: int
    product_id: int
    total_score: float
    tier: str
    icp_fit: float
    company_fit: float
    technology_fit: float
    intent_score: float
    geography_score: float
    components: List[ComponentScore]
    reasons: List[ScoreReason]
