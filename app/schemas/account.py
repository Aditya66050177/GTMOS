from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class AccountResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    country: Optional[str] = None
    description: Optional[str] = None
    technology_stack: Optional[List[str]] = None
    funding: Optional[str] = None
    support_team_size: Optional[int] = None
    stage: Optional[str] = "Research"
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
