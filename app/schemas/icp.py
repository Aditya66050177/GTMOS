from pydantic import BaseModel, Field
from typing import List, Optional

class ICPProfileSchema(BaseModel):
    industries: List[str] = Field(description="Target industry sectors")
    min_employees: int = Field(description="Minimum employee threshold")
    max_employees: int = Field(description="Maximum employee threshold")
    geographies: List[str] = Field(description="Target countries or regions")
    buyer_roles: List[str] = Field(description="Target decision maker roles")
    pain_points: List[str] = Field(description="Key customer pain points solved")
    technologies: List[str] = Field(description="Key technology stack requirements or integrations")
    buying_triggers: List[str] = Field(description="Signals indicating readiness to buy")
    exclusion_criteria: List[str] = Field(description="Criteria that disqualify an account")
