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


class EvidenceStatusCounts(BaseModel):
    current: int = 0
    aging: int = 0
    expired: int = 0
    superseded: int = 0
    rejected: int = 0


class PrioritizationRow(BaseModel):
    """One account in the prioritization table. Every value is read from stored scores and engine calls."""
    id: int
    name: str
    industry: Optional[str]
    country: Optional[str]
    employee_count: Optional[int]
    stage: str
    scored: bool
    fit: Optional[float] = Field(None, description="ICP + company + technology + geography fit, out of 80")
    intent: Optional[float] = Field(None, description="Stored intent score, out of 20")
    total: Optional[float] = None
    tier: Optional[str] = None
    action: Optional[str] = None
    rule_id: Optional[str] = None
    evidence: EvidenceStatusCounts
    uses_synthetic_demo_additions: bool = False
