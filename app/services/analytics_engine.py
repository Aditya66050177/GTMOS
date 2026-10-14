import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.models import Account, Score, Activity, Opportunity, Signal, Product, ICPProfile
from app.schemas.analytics import (
    FunnelTotals,
    StageConversion,
    FunnelAnalyticsResponse,
    WeeklyTrendPoint,
    TrendsAnalyticsResponse
)
from app.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """
    Deterministic Analytics Engine using SQL and pandas.
    Computes funnel metrics, stage-to-stage conversion rates, weekly trends,
    and performance breakdowns by tier, industry, and outreach angle.
    NO LLM usage.
    """

    def get_funnel_analytics(self, db: Session, product_id: Optional[int] = None) -> FunnelAnalyticsResponse:
        # Load Accounts and Scores into pandas DataFrame
        accounts = db.query(Account).all()
        if not accounts:
            empty_totals = FunnelTotals(
                total_accounts=0, high_priority_accounts=0,
                contacted=0, replies=0, meetings=0, opportunities=0, won=0, lost=0
            )
            return FunnelAnalyticsResponse(
                totals=empty_totals, stage_counts={}, conversions=[],
                performance_by_tier=[], performance_by_industry=[], performance_by_angle=[]
            )

        acc_data = []
        for a in accounts:
            acc_data.append({
                "id": a.id,
                "name": a.name,
                "industry": a.industry or "Unknown",
                "stage": a.stage or "Research",
                "employee_count": a.employee_count or 0
            })
        df_acc = pd.DataFrame(acc_data)

        # Load Scores
        scores = db.query(Score).all()
        score_dict = {}
        for s in scores:
            score_dict[s.account_id] = {
                "tier": s.tier or "Low",
                "total_score": s.total_score or 0.0,
                "intent_score": s.intent_score or 0.0
            }

        df_acc["tier"] = df_acc["id"].map(lambda aid: score_dict.get(aid, {}).get("tier", "Low"))
        df_acc["total_score"] = df_acc["id"].map(lambda aid: score_dict.get(aid, {}).get("total_score", 0.0))

        # Load Activities to determine historical stage reach
        activities = db.query(Activity).all()
        act_types_by_acc = {}
        for act in activities:
            act_types_by_acc.setdefault(act.account_id, set()).add(act.activity_type)

        df_acc["has_outreach"] = df_acc["id"].map(lambda aid: "outreach_sent" in act_types_by_acc.get(aid, set()) or df_acc.loc[df_acc["id"]==aid, "stage"].values[0] in ["Contacted", "Replied", "Meeting", "Opportunity", "Won"])
        df_acc["has_reply"] = df_acc["id"].map(lambda aid: "reply_received" in act_types_by_acc.get(aid, set()) or df_acc.loc[df_acc["id"]==aid, "stage"].values[0] in ["Replied", "Meeting", "Opportunity", "Won"])
        df_acc["has_meeting"] = df_acc["id"].map(lambda aid: "meeting_held" in act_types_by_acc.get(aid, set()) or df_acc.loc[df_acc["id"]==aid, "stage"].values[0] in ["Meeting", "Opportunity", "Won"])
        df_acc["has_opp"] = df_acc["id"].map(lambda aid: "opportunity_created" in act_types_by_acc.get(aid, set()) or df_acc.loc[df_acc["id"]==aid, "stage"].values[0] in ["Opportunity", "Won"])
        df_acc["is_won"] = df_acc["stage"] == "Won"
        df_acc["is_lost"] = df_acc["stage"] == "Lost"

        # Totals
        total_accounts = len(df_acc)
        high_priority = len(df_acc[df_acc["tier"].isin(["Priority 1", "Priority 2"])])
        contacted_count = int(df_acc["has_outreach"].sum())
        replies_count = int(df_acc["has_reply"].sum())
        meetings_count = int(df_acc["has_meeting"].sum())
        opps_count = int(df_acc["has_opp"].sum())
        won_count = int(df_acc["is_won"].sum())
        lost_count = int(df_acc["is_lost"].sum())

        totals = FunnelTotals(
            total_accounts=total_accounts,
            high_priority_accounts=high_priority,
            contacted=contacted_count,
            replies=replies_count,
            meetings=meetings_count,
            opportunities=opps_count,
            won=won_count,
            lost=lost_count
        )

        # Stage distribution
        stage_counts = df_acc["stage"].value_counts().to_dict()

        # Stage-to-Stage Conversions
        def calc_conv(from_c, to_c, from_name, to_name):
            rate = round((to_c / from_c * 100.0), 1) if from_c > 0 else 0.0
            return StageConversion(
                from_stage=from_name,
                to_stage=to_name,
                from_count=from_c,
                to_count=to_c,
                conversion_rate_pct=rate
            )

        conversions = [
            calc_conv(total_accounts, contacted_count, "Research", "Contacted"),
            calc_conv(contacted_count, replies_count, "Contacted", "Replied"),
            calc_conv(replies_count, meetings_count, "Replied", "Meeting"),
            calc_conv(meetings_count, opps_count, "Meeting", "Opportunity"),
            calc_conv(opps_count, won_count, "Opportunity", "Won"),
        ]

        # Breakdown by Tier
        tier_group = df_acc.groupby("tier")
        tier_perf = []
        for tier_name in ["Priority 1", "Priority 2", "Priority 3", "Low"]:
            if tier_name in tier_group.groups:
                grp = tier_group.get_group(tier_name)
                t_tot = len(grp)
                t_cont = int(grp["has_outreach"].sum())
                t_rep = int(grp["has_reply"].sum())
                t_meet = int(grp["has_meeting"].sum())
                t_won = int(grp["is_won"].sum())
                t_win_rate = round((t_won / t_tot * 100.0), 1) if t_tot > 0 else 0.0
                tier_perf.append({
                    "tier": tier_name,
                    "accounts": t_tot,
                    "contacted": t_cont,
                    "replies": t_rep,
                    "meetings": t_meet,
                    "won": t_won,
                    "win_rate_pct": t_win_rate
                })
            else:
                tier_perf.append({
                    "tier": tier_name, "accounts": 0, "contacted": 0, "replies": 0, "meetings": 0, "won": 0, "win_rate_pct": 0.0
                })

        # Breakdown by Industry
        ind_group = df_acc.groupby("industry")
        ind_perf = []
        for ind_name, grp in ind_group:
            i_tot = len(grp)
            i_cont = int(grp["has_outreach"].sum())
            i_rep = int(grp["has_reply"].sum())
            i_meet = int(grp["has_meeting"].sum())
            i_won = int(grp["is_won"].sum())
            ind_perf.append({
                "industry": ind_name,
                "accounts": i_tot,
                "contacted": i_cont,
                "replies": i_rep,
                "meetings": i_meet,
                "won": i_won,
                "conversion_rate_pct": round((i_won / i_tot * 100.0), 1) if i_tot > 0 else 0.0
            })
        ind_perf.sort(key=lambda x: x["accounts"], reverse=True)

        # Breakdown by Recommended Angle
        rec_engine = RecommendationEngine()
        signals = db.query(Signal).all()
        signals_by_acc = {}
        for sig in signals:
            signals_by_acc.setdefault(sig.account_id, []).append(sig)

        product = db.query(Product).first()
        icp = db.query(ICPProfile).filter_by(product_id=product.id).first() if product else None

        angles_list = []
        for a in accounts:
            sc_info = score_dict.get(a.id, {})
            score_obj = Score(tier=sc_info.get("tier", "Low"), intent_score=sc_info.get("intent_score", 0.0))
            acc_sigs = signals_by_acc.get(a.id, [])
            rec = rec_engine.get_recommendation(score_obj, acc_sigs, icp)
            angles_list.append(rec.suggested_angle or "General Outreach")

        df_acc["angle"] = angles_list
        angle_group = df_acc.groupby("angle")
        angle_perf = []
        for ang_name, grp in angle_group:
            a_tot = len(grp)
            a_cont = int(grp["has_outreach"].sum())
            a_rep = int(grp["has_reply"].sum())
            a_meet = int(grp["has_meeting"].sum())
            a_won = int(grp["is_won"].sum())
            angle_perf.append({
                "angle": ang_name,
                "accounts": a_tot,
                "contacted": a_cont,
                "replies": a_rep,
                "meetings": a_meet,
                "won": a_won,
                "reply_rate_pct": round((a_rep / a_cont * 100.0), 1) if a_cont > 0 else 0.0
            })
        angle_perf.sort(key=lambda x: x["accounts"], reverse=True)

        return FunnelAnalyticsResponse(
            totals=totals,
            stage_counts=stage_counts,
            conversions=conversions,
            performance_by_tier=tier_perf,
            performance_by_industry=ind_perf,
            performance_by_angle=angle_perf
        )

    def get_weekly_trends(self, db: Session) -> TrendsAnalyticsResponse:
        activities = db.query(Activity).order_by(Activity.timestamp.asc()).all()
        if not activities:
            return TrendsAnalyticsResponse(weekly_trends=[])

        data = []
        for act in activities:
            ts = act.timestamp or datetime.utcnow()
            week_label = ts.strftime("%Y-W%W")
            data.append({
                "week": week_label,
                "type": act.activity_type
            })

        df_act = pd.DataFrame(data)
        weeks = sorted(df_act["week"].unique())

        trends = []
        for wk in weeks:
            wk_df = df_act[df_act["week"] == wk]
            contacted = len(wk_df[wk_df["type"] == "outreach_sent"])
            replies = len(wk_df[wk_df["type"] == "reply_received"])
            meetings = len(wk_df[wk_df["type"] == "meeting_held"])
            opps = len(wk_df[wk_df["type"] == "opportunity_created"])
            won = len(wk_df[wk_df["type"] == "deal_won"])

            trends.append(WeeklyTrendPoint(
                week=wk,
                contacted=contacted,
                replies=replies,
                meetings=meetings,
                opportunities=opps,
                won=won
            ))

        return TrendsAnalyticsResponse(weekly_trends=trends)
