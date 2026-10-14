from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class ProductCreate(BaseModel):
    name: str
    description: str
    target_market: Optional[List[str]] = None
    geography: Optional[List[str]] = None
    price_range: Optional[str] = None

class ProductResponse(ProductCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
