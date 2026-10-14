from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime

class PersonalizationOutputSchema(BaseModel):
    why_this_account: str = Field(..., description="Explanation of why this account was selected and prioritized")
    message_draft: str = Field(..., description="Personalized outreach draft under 120 words referencing evidence")

class DraftResponse(BaseModel):
    id: int
    account_id: int
    contact_id: Optional[int] = None
    account_name: Optional[str] = None
    body: Optional[str] = None
    original_body: Optional[str] = None
    status: str
    evidence_ids: Optional[List[Any]] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class DraftUpdateRequest(BaseModel):
    body: str = Field(..., description="Updated message draft body")
