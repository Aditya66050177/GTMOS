from pydantic import BaseModel, Field
from typing import Optional

class RecommendationSchema(BaseModel):
    action: str = Field(..., description="Recommended action: CONTACT, RESEARCH, PRIORITIZE, NURTURE, DEPRIORITIZE")
    reason: str = Field(..., description="Deterministic rule-based explanation for the recommendation")
    suggested_persona: Optional[str] = Field(None, description="Suggested buyer persona role")
    suggested_angle: Optional[str] = Field(None, description="Suggested outreach angle based on signals")
