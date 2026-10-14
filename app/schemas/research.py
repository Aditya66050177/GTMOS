from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ResearchRequest(BaseModel):
    raw_text: str = Field(..., description="Raw text of the research")
    source: str = Field(..., description="Source of the text")
    date_str: str = Field(..., description="ISO 8601 date string")
