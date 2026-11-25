from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

class FunnelTotals(BaseModel):
    total_accounts: int
    high_priority_accounts: int
    contacted: int
    replies: int
    meetings: int
    opportunities: int
    won: int
    lost: int

class StageConversion(BaseModel):
    from_stage: str
    to_stage: str
    from_count: int
    to_count: int
    conversion_rate_pct: float

SIMULATED_PIPELINE_LABEL = ("Simulated pipeline: stages and activities come from a seeded 40-day simulation "
                            "on synthetic accounts. They are not real sales outcomes.")


class FunnelAnalyticsResponse(BaseModel):
    data_label: str = SIMULATED_PIPELINE_LABEL
    totals: FunnelTotals
    stage_counts: Dict[str, int]
    conversions: List[StageConversion]
    performance_by_tier: List[Dict[str, Any]]
    performance_by_industry: List[Dict[str, Any]]
    performance_by_angle: List[Dict[str, Any]]

class WeeklyTrendPoint(BaseModel):
    week: str
    contacted: int
    replies: int
    meetings: int
    opportunities: int
    won: int

class TrendsAnalyticsResponse(BaseModel):
    data_label: str = SIMULATED_PIPELINE_LABEL
    weekly_trends: List[WeeklyTrendPoint]

class AnalystQueryIntentSchema(BaseModel):
    function_name: str = Field(..., description="Mapped function: get_funnel_summary, get_conversion_rates, get_weekly_trends, get_tier_performance, get_industry_performance, get_angle_performance, or unknown")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the function")

class AnalystAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=300, description="Natural language question about GTM analytics")

class AnalystAskResponse(BaseModel):
    question: str
    function_called: str
    explanation: str
    data: Any
    observations: List[str] = Field(default_factory=list, description="Statements read directly off the returned data")
    hypotheses: List[str] = Field(default_factory=list, description="Labelled interpretations, not established facts")
    data_label: Optional[str] = None
    generated_by: str = "Predefined query; the model only chose which query to run"
