import streamlit as st
import pandas as pd
from datetime import datetime
from app.db.database import SessionLocal
from app.models import Draft, Account, Activity, Signal, Score, Opportunity
from app.services.crm_service import CRMService
from app.schemas.crm import PipelineStage, FORWARD_STAGE_ORDER

st.title("📊 CRM Pipeline & Outreach Review")

with SessionLocal() as db:
    crm = CRMService()

    # Top Navigation Mode: Kanban Pipeline Board vs Review Queue
    mode = st.radio("Navigation View", ["📈 Pipeline Kanban Board", "📋 Outreach Review Queue"], horizontal=True)

    if mode == "📈 Pipeline Kanban Board":
        st.subheader("Interactive Pipeline Board")

        # Load accounts, scores, and opportunities
        accounts = db.query(Account).all()
        scores = {s.account_id: s for s in db.query(Score).all()}
        opps = {o.account_id: o for o in db.query(Opportunity).all()}

        # Group accounts by stage
        stages_list = [s.value for s in PipelineStage]
        stage_groups = {s: [] for s in stages_list}
        for a in accounts:
            stg = a.stage or "Research"
            if stg not in stage_groups:
                stg = "Research"
            stage_groups[stg].append(a)

        # Render stage summary metrics
        cols = st.columns(len(stages_list))
        for idx, stg_name in enumerate(stages_list):
            with cols[idx]:
                cnt = len(stage_groups[stg_name])
                st.metric(label=stg_name, value=cnt)

        st.markdown("---")

        # Kanban columns display
        kanban_cols = st.columns(len(stages_list))
        for idx, stg_name in enumerate(stages_list):
            with kanban_cols[idx]:
                st.markdown(f"### {stg_name} ({len(stage_groups[stg_name])})")
                acc_list = stage_groups[stg_name]
                if not acc_list:
                    st.caption("No accounts in stage.")
                for acc in acc_list[:12]:
                    with st.container(border=True):
                        sc = scores.get(acc.id)
                        tier_badge = sc.tier if sc else "Low"
                        st.markdown(f"**{acc.name}**")
                        st.caption(f"{acc.industry} • Tier: `{tier_badge}`")
                        
                        opp = opps.get(acc.id)
                        if opp and opp.deal_value:
                            st.caption(f"💰 Deal: ${opp.deal_value:,.0f}")

                        # Stage advance selector
                        available_targets = [
                            s.value for s in PipelineStage
                            if crm.is_valid_transition(stg_name, s.value) and s.value != stg_name
                        ]
                        if available_targets:
                            target_stg = st.selectbox(
                                "Move to:",
                                options=["-"] + available_targets,
                                key=f"move_{acc.id}_{stg_name}"
                            )
                            if target_stg != "-":
                                try:
                                    crm.update_account_stage(db, acc.id, target_stg)
                                    st.success(f"Moved {acc.name} to {target_stg}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                if len(acc_list) > 12:
                    st.caption(f"+ {len(acc_list) - 12} more accounts")

    else:
        # Review Queue View
        st.subheader("Outreach Review Queue & Manual Dispatch")
        st.markdown("All AI-generated messages require human review. Marking as sent manually moves the account to `Contacted`.")

        pending_count = db.query(Draft).filter_by(status="pending").count()
        approved_count = db.query(Draft).filter_by(status="approved").count()
        rejected_count = db.query(Draft).filter_by(status="rejected").count()
        sent_count = db.query(Draft).filter_by(status="sent").count()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pending Review", pending_count, delta="Awaiting Approval" if pending_count > 0 else None)
        c2.metric("Approved (Ready to Send)", approved_count)
        c3.metric("Sent (Contacted)", sent_count)
        c4.metric("Rejected", rejected_count)

        st.markdown("---")

        tab_pending, tab_approved, tab_rejected, tab_all = st.tabs([
            f"⏳ Pending ({pending_count})",
            f"✅ Approved ({approved_count})",
            f"❌ Rejected ({rejected_count})",
            "📂 All Drafts"
        ])

        def render_draft_list(drafts, allow_actions=True, is_approved_view=False):
            if not drafts:
                st.info("No drafts in this category.")
                return

            for d in drafts:
                acc = db.query(Account).filter_by(id=d.account_id).first()
                acc_name = acc.name if acc else f"Account #{d.account_id}"

                with st.container(border=True):
                    head_col1, head_col2 = st.columns([3, 1])
                    with head_col1:
                        status_badge = {
                            "pending": "🟡 PENDING REVIEW",
                            "approved": "🟢 APPROVED",
                            "sent": "📬 SENT (CONTACTED)",
                            "rejected": "🔴 REJECTED"
                        }.get(d.status, d.status.upper())
                        st.markdown(f"#### Draft #{d.id} — **{acc_name}** (`{status_badge}`)")
                        if d.created_at:
                            st.caption(f"Created: {d.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    
                    with head_col2:
                        if d.evidence_ids:
                            ev_signals = db.query(Signal).filter(Signal.id.in_(d.evidence_ids)).all()
                            st.markdown(f"**Referenced Signals:** {len(ev_signals)}")

                    if d.status == "pending" and allow_actions:
                        edited_body = st.text_area(
                            "Message Body (Edit before approving):",
                            value=d.body or "",
                            height=120,
                            key=f"edit_body_{d.id}"
                        )
                        
                        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
                        with btn_col1:
                            if st.button("✅ Approve", key=f"app_{d.id}", type="primary"):
                                d.body = edited_body
                                d.status = "approved"
                                d.reviewed_at = datetime.utcnow()
                                activity = Activity(
                                    account_id=d.account_id,
                                    contact_id=d.contact_id,
                                    activity_type="outreach_approved",
                                    status="approved",
                                    activity_metadata={"draft_id": d.id, "body": d.body}
                                )
                                db.add(activity)
                                db.commit()
                                st.success(f"Draft #{d.id} approved!")
                                st.rerun()

                        with btn_col2:
                            if st.button("❌ Reject", key=f"rej_{d.id}"):
                                d.body = edited_body
                                d.status = "rejected"
                                d.reviewed_at = datetime.utcnow()
                                db.commit()
                                st.warning(f"Draft #{d.id} rejected.")
                                st.rerun()

                        with btn_col3:
                            if edited_body != d.body:
                                if st.button("💾 Save Changes", key=f"save_{d.id}"):
                                    d.body = edited_body
                                    db.commit()
                                    st.info("Draft body updated.")
                                    st.rerun()

                    elif d.status == "approved" and is_approved_view:
                        st.text_area("Approved Message Body:", value=d.body or "", height=100, key=f"app_body_{d.id}", disabled=True)
                        if st.button("📬 Mark as Sent (Advances to Contacted)", key=f"send_{d.id}", type="primary"):
                            crm.mark_outreach_sent(db, d.account_id, draft_id=d.id)
                            st.success(f"Marked as sent! {acc_name} advanced to Contacted stage.")
                            st.rerun()
                    else:
                        st.text_area("Message Body:", value=d.body or "", height=100, key=f"view_body_{d.id}", disabled=True)

        with tab_pending:
            drafts = db.query(Draft).filter_by(status="pending").order_by(Draft.created_at.desc()).all()
            render_draft_list(drafts, allow_actions=True)

        with tab_approved:
            drafts = db.query(Draft).filter_by(status="approved").order_by(Draft.reviewed_at.desc()).all()
            render_draft_list(drafts, allow_actions=False, is_approved_view=True)

        with tab_rejected:
            drafts = db.query(Draft).filter_by(status="rejected").order_by(Draft.reviewed_at.desc()).all()
            render_draft_list(drafts, allow_actions=False)

        with tab_all:
            drafts = db.query(Draft).order_by(Draft.created_at.desc()).all()
            render_draft_list(drafts, allow_actions=True)
