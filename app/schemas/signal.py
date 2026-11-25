from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional
from datetime import datetime

class SignalSchema(BaseModel):
    type: str = Field(..., description="Type of signal, e.g., support_hiring, funding, product_launch, international_expansion, relevant_technology, rapid_growth, executive_change, too_small, wrong_industry, wrong_geography, no_use_case")
    description: str = Field(..., description="Brief summary of the signal")
    strength: float = Field(..., ge=0.0, le=1.0, description="Strength of the signal from 0 to 1")
    source: str = Field(..., description="Source of the signal (e.g., News, Job Board, Company Website)")
    detected_at: datetime = Field(..., description="When the signal occurred or was published in ISO format")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the extraction from 0 to 1")
    evidence: str = Field(..., description="Exact text from the raw input that proves this signal")

    model_config = ConfigDict(from_attributes=True)

RejectionCategory = Literal["negated", "unsupported", "ambiguous"]


class RejectedClaimSchema(BaseModel):
    """A sentence that talks about a buying signal but must not count as one."""
    sentence: str = Field(..., description="Exact sentence from the raw text")
    category: RejectionCategory = Field(..., description="negated: contradicted; unsupported: hearsay or not in the source; ambiguous: speculative")
    reason: str = Field(..., description="Short, specific reason")
    claimed_type: Optional[str] = Field(None, description="Signal type the sentence seemed to claim")


class SignalListSchema(BaseModel):
    signals: List[SignalSchema]
    rejected: List[RejectedClaimSchema] = Field(default_factory=list)
