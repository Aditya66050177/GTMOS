from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1, max_length=2_000)
    target_market: Optional[List[str]] = Field(None, max_length=20)
    geography: Optional[List[str]] = Field(None, max_length=20)
    price_range: Optional[str] = Field(None, max_length=120)

class ProductResponse(ProductCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
