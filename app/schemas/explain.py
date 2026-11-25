"""Response schemas for the explainability endpoints (/web/accounts/{id}/explain, /web/compare)."""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SignalStatus = Literal["current", "aging", "expired", "superseded", "disqualifier", "not_weighted"]


class ReasonOut(BaseModel):
    rule: str
    met: bool
    text: str
    points: float


class FitComponentOut(BaseModel):
    name: str
    score: float
    max_score: float
    reasons: List[ReasonOut]


class FitOut(BaseModel):
    score: float = Field(..., description="Sum of ICP, company, technology and geography fit")
    max_score: float = 80.0
    meaning: str
    components: List[FitComponentOut]


class SignalContributionOut(BaseModel):
    signal_id: int
    signal_type: str
    label: str
    status: SignalStatus
    counted: bool = Field(..., description="False when an older signal of the same type was superseded")
    source: Optional[str]
    detected_at: Optional[datetime]
    days_old: int
    quote: Optional[str] = Field(None, description="Exact supporting text stored with the signal")
    source_sentence: Optional[str] = Field(None, description="Sentence of the original research note that contains the quote; null if the note was not recorded")
    weight: float
    strength: float
    confidence: float
    decay: float
    points: float = Field(..., description="weight x strength x confidence x decay (0 if not counted)")
    why_it_matters: Optional[str] = Field(None, description="Product hypothesis for this signal type, not a verified fact")


class RecencyRulesOut(BaseModel):
    current_max_days: int
    aging_max_days: int
    aging_decay: float
    formula: str = "points = weight x strength x confidence x decay; newest signal per type counts; intent = clamp(sum, 0, 20)"


class IntentOut(BaseModel):
    score: float = Field(..., description="Stored intent score used in the total")
    max_score: float = 20.0
    meaning: str
    raw_total: float = Field(..., description="Sum of contributions before clamping to 0-20")
    clamped: bool
    recomputed_score: float
    matches_stored_score: bool
    as_of: datetime
    buying_signals: List[SignalContributionOut]
    disqualifiers: List[SignalContributionOut]
    recency_rules: RecencyRulesOut


class RejectedEvidenceOut(BaseModel):
    sentence: Optional[str]
    category: str = Field(..., description="negated, unsupported or ambiguous")
    reason: Optional[str]
    claimed_type: Optional[str]
    source: Optional[str]
    date: Optional[str]
    dataset: Optional[str]
    points: float = 0.0


class TierOut(BaseModel):
    total: float
    max_score: float = 100.0
    tier: str
    rule: str


class RecommendationOut(BaseModel):
    action: str
    rule_id: str
    rule: str
    reason: str
    suggested_persona: Optional[str]
    suggested_angle: Optional[str]


class ResearchNoteOut(BaseModel):
    source: Optional[str]
    date: Optional[str]
    dataset: Optional[str]
    label: Optional[str]
    raw_text: Optional[str]
    signals_extracted: int


class EvidenceSummaryOut(BaseModel):
    buying_signals: int
    counted: int
    current: int
    aging: int
    expired: int
    superseded: int
    disqualifiers: int
    rejected: int


class AccountRefOut(BaseModel):
    id: int
    name: str
    industry: Optional[str]
    employee_count: Optional[int]
    country: Optional[str]
    stage: Optional[str]


class AccountExplanation(BaseModel):
    account: AccountRefOut
    data_label: str
    fit: FitOut
    intent: IntentOut
    total: TierOut
    recommendation: RecommendationOut
    disqualification_reasons: List[str]
    rejected_evidence: List[RejectedEvidenceOut]
    research_notes: List[ResearchNoteOut]
    evidence_summary: EvidenceSummaryOut
    includes_synthetic_demo_additions: bool


class ComparisonOut(BaseModel):
    accounts: List[AccountExplanation]
    observations: List[str] = Field(..., description="Deterministic statements derived only from the numbers above")


class FeaturedComparisonOut(BaseModel):
    title: str
    selection_rule: str
    account_ids: List[int]
