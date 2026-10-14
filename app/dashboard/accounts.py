import streamlit as st
import pandas as pd
from app.db.database import SessionLocal
from app.models import Account, Score, Product
from app.services.research_engine import ResearchEngine
from app.services.scoring_engine import ScoringEngine
from app.services.icp_engine import ICPEngine

st.title("🏢 Accounts Management & Fit Scoring")

with SessionLocal() as db:
    accounts_count = db.query(Account).count()
    if accounts_count == 0:
        re = ResearchEngine()
        re.load_accounts_from_csv(db)

    products = db.query(Product).all()
    if not products:
        p = Product(
            name="AI Customer Support Assistant",
            description="Autonomous AI agent platform for automating B2B customer support tickets.",
            target_market=["B2B SaaS", "Software"],
            geography=["US", "Canada"],
            price_range="$10,000 - $50,000"
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        icp_e = ICPEngine()
        icp_e.generate_icp_for_product(db, p)
        products = [p]

    selected_product_id = st.selectbox(
        "Select Product for ICP Fit Scoring",
        options=[p.id for p in products],
        format_func=lambda pid: next((p.name for p in products if p.id == pid), f"Product {pid}")
    )

    product = db.query(Product).filter_by(id=selected_product_id).first()

    scores_count = db.query(Score).filter_by(product_id=selected_product_id).count()
    if scores_count == 0 and product:
        st.info("Accounts have not been scored for this product yet.")
        if st.button("⚡ Score All Accounts Now"):
            se = ScoringEngine()
            all_accs = db.query(Account).all()
            for a in all_accs:
                se.score_account(db, a, product)
            st.rerun()

    results = (
        db.query(Account, Score)
        .outerjoin(Score, (Account.id == Score.account_id) & (Score.product_id == selected_product_id))
        .all()
    )

    table_data = []
    for acc, sc in results:
        tot = sc.total_score if sc else 0.0
        tr = sc.tier if sc else "Unscored"
        table_data.append({
            "Account ID": acc.id,
            "Company Name": acc.name,
            "Domain": acc.domain or "",
            "Industry": acc.industry or "",
            "Employees": acc.employee_count or 0,
            "Country": acc.country or "",
            "Support Team": acc.support_team_size or 0,
            "Total Score": tot,
            "Priority Tier": tr
        })

    df = pd.DataFrame(table_data)
    if not df.empty:
        df = df.sort_values(by="Total Score", ascending=False).reset_index(drop=True)
        df["Rank"] = df.index + 1

    st.subheader(f"Target Accounts Ranking ({len(df)} Accounts)")
    st.dataframe(
        df[["Rank", "Company Name", "Domain", "Industry", "Employees", "Country", "Total Score", "Priority Tier"]],
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.subheader("🔍 Account Score Breakdown & Provenance")

    if not df.empty:
        acc_options = {row["Company Name"]: row["Account ID"] for _, row in df.iterrows()}
        selected_company = st.selectbox("Select an Account to inspect score details:", options=list(acc_options.keys()))

        selected_acc_id = acc_options[selected_company]
        target_account = db.query(Account).filter_by(id=selected_acc_id).first()
        target_score = db.query(Score).filter_by(account_id=selected_acc_id, product_id=selected_product_id).first()

        col_l, col_r = st.columns([1, 2])

        with col_l:
            st.markdown("#### Account Details")
            st.write(f"**Name:** {target_account.name}")
            st.write(f"**Domain:** {target_account.domain}")
            st.write(f"**Industry:** {target_account.industry}")
            st.write(f"**Employees:** {target_account.employee_count}")
            st.write(f"**Country:** {target_account.country}")
            st.write(f"**Support Team Size:** {target_account.support_team_size}")
            st.write(f"**Funding:** {target_account.funding}")
            st.write(f"**Tech Stack:** {', '.join(target_account.technology_stack or [])}")
            st.write(f"**Description:** {target_account.description}")

        with col_r:
            st.markdown("#### Fit Score Breakdown")
            if target_score:
                st.metric(
                    label="Total ICP Score",
                    value=f"{target_score.total_score} / 100",
                    delta=target_score.tier
                )

                reasoning = target_score.reasoning or {}
                components_data = reasoning.get("components", [])
                reasons_data = reasoning.get("reasons", [])

                st.markdown("##### Component Scores")
                comp_df = pd.DataFrame(components_data)
                if not comp_df.empty:
                    comp_df.columns = ["Component", "Score", "Max Score"]
                    st.dataframe(comp_df, use_container_width=True, hide_index=True)

                st.markdown("##### Score Reasons & Rules")
                for r in reasons_data:
                    status_icon = "✅" if r.get("met") else "❌"
                    pts_str = f"+{r.get('points')}" if r.get('points', 0) >= 0 else f"{r.get('points')}"
                    st.write(f"{status_icon} **{r.get('rule')}** ({pts_str} pts): {r.get('text')}")
            else:
                st.warning("Account not yet scored for this product.")

        st.markdown("---")
        
        # ── Recommended Action Card & Outreach Generation ─────────────────
        from app.services.recommendation_engine import RecommendationEngine
        from app.services.personalization import PersonalizationEngine
        from app.models import Draft, ICPProfile, Signal, Activity

        icp = db.query(ICPProfile).filter_by(product_id=selected_product_id).first()
        signals = db.query(Signal).filter_by(account_id=selected_acc_id).order_by(Signal.detected_at.desc()).all()
        rec_engine = RecommendationEngine()
        recommendation = rec_engine.get_recommendation(target_score or {}, signals, icp)

        st.subheader("🎯 Recommended Action & Outreach Strategy")
        
        rec_col1, rec_col2 = st.columns([1, 1])
        with rec_col1:
            action_badge_color = {
                "CONTACT": "🟢",
                "PRIORITIZE": "🔥",
                "RESEARCH": "🔍",
                "NURTURE": "🌱",
                "DEPRIORITIZE": "⛔"
            }.get(recommendation.action, "📌")
            
            st.markdown(f"### {action_badge_color} Action: **`{recommendation.action}`**")
            st.info(f"**Rationale:** {recommendation.reason}")

        with rec_col2:
            st.markdown(f"**Suggested Persona:** `{recommendation.suggested_persona or 'VP Support'}`")
            st.markdown(f"**Suggested Angle:** `{recommendation.suggested_angle or 'Efficiency'}`")
            
            # Action button
            if recommendation.action == "DEPRIORITIZE":
                st.button("⛔ Generate Outreach Draft", disabled=True, help="Outreach cannot be generated for DEPRIORITIZE accounts.")
            else:
                if st.button("✉️ Generate Outreach Draft", key=f"gen_draft_{selected_acc_id}"):
                    p_engine = PersonalizationEngine()
                    try:
                        draft = p_engine.generate_draft(db, selected_acc_id, selected_product_id)
                        st.success(f"✅ Generated draft #{draft.id} successfully! Moved to Review Queue.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error generating draft: {e}")

        # Show existing drafts for this account
        account_drafts = db.query(Draft).filter_by(account_id=selected_acc_id).order_by(Draft.created_at.desc()).all()
        if account_drafts:
            with st.expander(f"📝 View Drafts for {target_account.name} ({len(account_drafts)})"):
                for d in account_drafts:
                    st.markdown(f"**Draft #{d.id}** — Status: `{d.status.upper()}` | Created: {d.created_at.strftime('%Y-%m-%d %H:%M') if d.created_at else 'N/A'}")
                    st.text_area("Message Body", value=d.body or "", height=80, key=f"acc_draft_body_{d.id}", disabled=True)

        st.markdown("---")
        st.subheader("📡 Signals & Intent Evidence")
        
        rejected_count = db.query(Activity).filter_by(account_id=selected_acc_id, activity_type="rejected_signal").count()
        
        st.write(f"**Rejected Unsupported Claims:** {rejected_count}")
        
        if signals:
            sig_data = []
            for sig in signals:
                st_label = "HIGH" if sig.strength and sig.strength >= 0.8 else ("MEDIUM" if sig.strength and sig.strength >= 0.5 else "LOW")
                dt_str = sig.detected_at.strftime('%Y-%m-%d') if sig.detected_at else "Unknown"
                
                sig_data.append({
                    "Type": sig.signal_type,
                    "Strength": st_label,
                    "Date": dt_str,
                    "Confidence": f"{(sig.confidence or 0.0) * 100:.0f}%",
                    "Source": sig.source or "N/A",
                    "Evidence": sig.evidence or "N/A"
                })
                
            st.table(pd.DataFrame(sig_data))
        else:
            st.info("No signals found for this account.")
