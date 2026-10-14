import streamlit as st
import pandas as pd
from app.db.database import SessionLocal
from app.models import Account, Signal, Activity

st.title("📡 Signals Intelligence")

with SessionLocal() as db:
    signals = (
        db.query(Signal, Account.name)
        .join(Account)
        .order_by(Signal.detected_at.desc())
        .limit(100)
        .all()
    )
    
    rejected_total = db.query(Activity).filter_by(activity_type="rejected_signal").count()
    st.metric(label="Total Unsupported Claims Rejected (Code Checked)", value=rejected_total)
    
    if not signals:
        st.info("No signals collected yet. Run the Research Engine.")
    else:
        st.subheader("Latest Intent Signals")
        data = []
        for sig, acc_name in signals:
            st_label = "HIGH" if sig.strength and sig.strength >= 0.8 else ("MEDIUM" if sig.strength and sig.strength >= 0.5 else "LOW")
            dt_str = sig.detected_at.strftime('%Y-%m-%d') if sig.detected_at else "Unknown"
            data.append({
                "Account": acc_name,
                "Type": sig.signal_type,
                "Strength": st_label,
                "Date": dt_str,
                "Evidence": sig.evidence or "N/A"
            })
            
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
