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

class FunnelAnalyticsResponse(BaseModel):
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
    weekly_trends: List[WeeklyTrendPoint]

class AnalystQueryIntentSchema(BaseModel):
    function_name: str = Field(..., description="Mapped function: get_funnel_summary, get_conversion_rates, get_weekly_trends, get_tier_performance, get_industry_performance, get_angle_performance, or unknown")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters to pass to the function")

class AnalystAskRequest(BaseModel):
    question: str = Field(..., description="Natural language question about GTM analytics")

class AnalystAskResponse(BaseModel):
    question: str
    function_called: str
    explanation: str
    data: Any
