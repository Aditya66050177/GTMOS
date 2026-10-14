import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st
import pandas as pd
import json
from app.db.database import SessionLocal
from app.services.analytics_engine import AnalyticsEngine
from app.services.analyst_service import AnalystService

st.title("📈 GTM Analytics & AI Analyst")

with SessionLocal() as db:
    analytics_engine = AnalyticsEngine()
    analyst_service = AnalystService()

    funnel_data = analytics_engine.get_funnel_analytics(db)
    trends_data = analytics_engine.get_weekly_trends(db)

    # 1. Top KPI Tiles
    totals = funnel_data.totals
    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    k1.metric("Total Accounts", totals.total_accounts)
    k2.metric("High Priority", totals.high_priority_accounts)
    k3.metric("Contacted", totals.contacted)
    k4.metric("Replies", totals.replies)
    k5.metric("Meetings", totals.meetings)
    k6.metric("Opportunities", totals.opportunities)
    k7.metric("Won", totals.won, delta="Closed Deals" if totals.won > 0 else None)

    st.markdown("---")

    # 2. Funnel Visualization & Stage Conversions
    col_chart, col_conv = st.columns([1, 1])

    with col_chart:
        st.subheader("🎯 Pipeline Stage Distribution")
        stage_df = pd.DataFrame([
            {"Stage": "Research", "Count": funnel_data.stage_counts.get("Research", 0)},
            {"Stage": "Contacted", "Count": funnel_data.stage_counts.get("Contacted", 0)},
            {"Stage": "Replied", "Count": funnel_data.stage_counts.get("Replied", 0)},
            {"Stage": "Meeting", "Count": funnel_data.stage_counts.get("Meeting", 0)},
            {"Stage": "Opportunity", "Count": funnel_data.stage_counts.get("Opportunity", 0)},
            {"Stage": "Won", "Count": funnel_data.stage_counts.get("Won", 0)},
            {"Stage": "Lost", "Count": funnel_data.stage_counts.get("Lost", 0)}
        ])
        st.bar_chart(stage_df.set_index("Stage"))

    with col_conv:
        st.subheader("🔄 Stage-to-Stage Conversion Rates")
        conv_list = []
        for c in funnel_data.conversions:
            conv_list.append({
                "Transition": f"{c.from_stage} ➔ {c.to_stage}",
                "From Count": c.from_count,
                "To Count": c.to_count,
                "Conversion Rate": f"{c.conversion_rate_pct:.1f}%"
            })
        st.dataframe(pd.DataFrame(conv_list), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 3. Weekly Trends
    st.subheader("📅 Weekly Activity & Conversion Trends")
    if trends_data.weekly_trends:
        trend_rows = [w.model_dump() for w in trends_data.weekly_trends]
        trend_df = pd.DataFrame(trend_rows).set_index("week")
        st.line_chart(trend_df[["contacted", "replies", "meetings", "opportunities", "won"]])
    else:
        st.info("No activity logged yet to plot weekly trends.")

    st.markdown("---")

    # 4. Performance Breakdowns
    st.subheader("📊 Performance Segmentation")
    tab_tier, tab_ind, tab_angle = st.tabs(["🏆 Performance by Fit Tier", "🏢 Performance by Industry", "🎯 Performance by Angle"])

    with tab_tier:
        st.dataframe(pd.DataFrame(funnel_data.performance_by_tier), use_container_width=True, hide_index=True)

    with tab_ind:
        st.dataframe(pd.DataFrame(funnel_data.performance_by_industry), use_container_width=True, hide_index=True)

    with tab_angle:
        st.dataframe(pd.DataFrame(funnel_data.performance_by_angle), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 5. Ask the AI GTM Analyst
    st.subheader("🤖 Ask the AI GTM Analyst")
    st.caption("Ask natural language questions about funnel metrics, stage drop-offs, weekly trends, or segment win rates. Code routes queries to deterministic functions, and the LLM cites only verified numbers.")

    sample_questions = [
        "What are the stage-to-stage conversion rates across the pipeline?",
        "How did weekly contacts and meetings trend over time?",
        "What is our performance and win rate by fit tier?",
        "Which industries have the highest conversion rate?",
        "Which outreach angle is driving the highest reply rate?",
        "What are our overall funnel totals and pipeline summary?"
    ]

    selected_sample = st.selectbox("Or choose a sample question:", ["-- Select a question --"] + sample_questions)
    
    default_q = selected_sample if selected_sample != "-- Select a question --" else "What is our overall funnel summary?"
    user_query = st.text_input("Enter your analytics question:", value=default_q)

    if st.button("🔍 Ask Analyst", type="primary"):
        if user_query.strip():
            with st.spinner("Analyzing verified metrics..."):
                response = analyst_service.ask(db, user_query.strip())

                st.markdown(f"### 💡 Analyst Insight (`{response.function_called}`)")
                st.success(response.explanation)

                with st.expander("🔢 View Structured Data Used by Analyst"):
                    st.json(response.data)
        else:
            st.warning("Please enter a question.")
