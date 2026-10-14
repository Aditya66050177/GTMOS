import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.services.analytics_engine import AnalyticsEngine
from app.schemas.analytics import (
    AnalystQueryIntentSchema,
    AnalystAskResponse
)
from app.ai.llm import LLMService
from app.ai.prompts import ANALYST_ROUTING_PROMPT, ANALYST_EXPLAIN_PROMPT

logger = logging.getLogger(__name__)

class AnalystExplanationSchema(BaseModel):
    explanation: str = Field(..., description="Short, factual executive explanation citing only the provided numbers")

class AnalystService:
    """
    AI GTM Analyst Service.
    Maps natural language questions to deterministic analytics functions, executes them,
    and prompts the LLM to synthesize a grounded explanation citing only the returned numbers.
    The LLM NEVER writes SQL or computes arithmetic directly.
    """
    def __init__(self, llm: Optional[LLMService] = None):
        self.llm = llm or LLMService()
        self.analytics_engine = AnalyticsEngine()

    def ask(self, db: Session, question: str) -> AnalystAskResponse:
        # Step 1: Map question to predefined function
        route_prompt = ANALYST_ROUTING_PROMPT.format(question=question)
        intent: AnalystQueryIntentSchema = self.llm.generate_structured(route_prompt, AnalystQueryIntentSchema)

        func_name = intent.function_name

        if func_name == "unknown":
            return AnalystAskResponse(
                question=question,
                function_called="unknown",
                explanation="This question cannot be mapped to our available analytics metrics. You can ask about funnel totals, stage-to-stage conversions, weekly trends, tier performance, industry breakdowns, or outreach angles.",
                data={}
            )

        # Step 2: Deterministic execution of predefined function
        funnel_res = None
        data = {}

        if func_name == "get_funnel_summary":
            funnel_res = self.analytics_engine.get_funnel_analytics(db)
            data = {
                "totals": funnel_res.totals.model_dump(),
                "stage_counts": funnel_res.stage_counts
            }
        elif func_name == "get_conversion_rates":
            funnel_res = self.analytics_engine.get_funnel_analytics(db)
            data = {"conversions": [c.model_dump() for c in funnel_res.conversions]}
        elif func_name == "get_weekly_trends":
            trends_res = self.analytics_engine.get_weekly_trends(db)
            data = {"weekly_trends": [w.model_dump() for w in trends_res.weekly_trends]}
        elif func_name == "get_tier_performance":
            funnel_res = self.analytics_engine.get_funnel_analytics(db)
            data = {"performance_by_tier": funnel_res.performance_by_tier}
        elif func_name == "get_industry_performance":
            funnel_res = self.analytics_engine.get_funnel_analytics(db)
            data = {"performance_by_industry": funnel_res.performance_by_industry[:8]}
        elif func_name == "get_angle_performance":
            funnel_res = self.analytics_engine.get_funnel_analytics(db)
            data = {"performance_by_angle": funnel_res.performance_by_angle}
        else:
            return AnalystAskResponse(
                question=question,
                function_called="unknown",
                explanation="Unrecognized analytics function requested.",
                data={}
            )

        # Step 3: LLM explains data using only returned numbers
        explain_prompt = ANALYST_EXPLAIN_PROMPT.format(
            question=question,
            function_name=func_name,
            data_json=json.dumps(data, indent=2)
        )

        try:
            explanation_obj: AnalystExplanationSchema = self.llm.generate_structured(
                explain_prompt, AnalystExplanationSchema
            )
            explanation_text = explanation_obj.explanation
        except Exception as e:
            logger.warning(f"Error generating LLM explanation: {e}")
            explanation_text = f"Executed {func_name} successfully with verified metrics from the analytics engine."

        return AnalystAskResponse(
            question=question,
            function_called=func_name,
            explanation=explanation_text,
            data=data
        )
