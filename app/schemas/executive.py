"""Response schemas for executive questions (/web/executive/*) and analyst answers."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Observation(BaseModel):
    """A statement read directly off database values."""
    text: str
    value: Optional[float] = None


class Hypothesis(BaseModel):
    """An interpretation. Plausible, explicitly not established by the data."""
    text: str
    label: str = "Hypothesis: not established by the data"


class AccountItem(BaseModel):
    id: int
    name: str
    stage: Optional[str]
    tier: Optional[str]
    total: Optional[float]
    fit: Optional[float]
    intent: Optional[float]
    action: Optional[str]
    rule_id: Optional[str]
    why: List[str] = Field(default_factory=list, description="Data-backed reasons this account is listed")
    evidence: Optional[str] = Field(None, description="Strongest counted signal quote, if any")
    uses_synthetic_demo_additions: bool = Field(False, description="Evidence includes a labelled synthetic demo note")


class ExecutiveAnswer(BaseModel):
    question_id: str
    question: str
    summary: str = Field(..., description="One-sentence answer built only from the observations")
    observations: List[Observation]
    hypotheses: List[Hypothesis]
    accounts: List[AccountItem] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    selection_rules: List[str] = Field(default_factory=list)
    data_sources: List[str]
    data_provenance: Dict[str, str]
    data_quality: List[str] = Field(default_factory=list, description="Missing or inconsistent records found")
    generated_by: str = "Deterministic database query (no LLM)"


class ExecutiveQuestionRef(BaseModel):
    id: str
    question: str
    endpoint: str
