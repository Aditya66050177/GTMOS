from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class PipelineStage(str, Enum):
    RESEARCH = "Research"
    CONTACTED = "Contacted"
    REPLIED = "Replied"
    MEETING = "Meeting"
    OPPORTUNITY = "Opportunity"
    WON = "Won"
    LOST = "Lost"

# Ordered forward stages
FORWARD_STAGE_ORDER = [
    PipelineStage.RESEARCH,
    PipelineStage.CONTACTED,
    PipelineStage.REPLIED,
    PipelineStage.MEETING,
    PipelineStage.OPPORTUNITY,
    PipelineStage.WON
]

class StageUpdateRequest(BaseModel):
    stage: PipelineStage = Field(..., description="Target pipeline stage")
    notes: Optional[str] = Field(None, description="Optional reason or notes for stage transition")

class ContactCreateRequest(BaseModel):
    name: str = Field(..., description="Full name of contact")
    role: Optional[str] = Field(None, description="Job title / buyer role")
    email: Optional[str] = Field(None, description="Email address")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")

class ContactResponse(BaseModel):
    id: int
    account_id: int
    name: str
    role: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ActivityResponse(BaseModel):
    id: int
    account_id: int
    contact_id: Optional[int] = None
    activity_type: Optional[str] = None
    status: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)

class PipelineStageGroup(BaseModel):
    stage: str
    count: int
    accounts: List[Dict[str, Any]]

class PipelineResponse(BaseModel):
    total_accounts: int
    stages: Dict[str, PipelineStageGroup]
