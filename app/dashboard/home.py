import streamlit as st
import requests
from pathlib import Path
from app.db.database import SessionLocal
from app.models import Product, ICPProfile, Account
from app.services.icp_engine import ICPEngine
from app.services.scoring_engine import ScoringEngine
from app.services.research_engine import ResearchEngine

st.set_page_config(page_title="GTMOS Command Center", page_icon="🎯", layout="wide")

current_dir = Path(__file__).parent

def home_page():
    st.title("🎯 GTMOS Command Center")
    st.subheader("System Health Status")

    api_url = "http://127.0.0.1:8000/health"
    try:
        response = requests.get(api_url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            st.success(f"✅ API Status: {data.get('status')} | Database: {data.get('database')}")
        else:
            st.warning(f"⚠️ API status code: {response.status_code}")
    except Exception:
        st.info("ℹ️ Local backend active via direct service integration.")

    st.markdown("---")
    st.subheader("🚀 Product Setup & GTM Strategy Generation")

    with st.form("product_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Product Name", value="AI Customer Support Assistant")
            price_range = st.text_input("Price Range", value="$10,000 - $50,000 / year")
            target_market = st.text_input("Target Market (comma separated)", value="B2B SaaS, Cloud Services, Software")
        with col2:
            geography = st.text_input("Target Geography (comma separated)", value="US, Canada, North America")
            description = st.text_area(
                "Product Description",
                value="Autonomous AI agent platform for automating B2B customer support tickets, resolving repetitive help desk overload, and improving response times.",
                height=100
            )

        submit_btn = st.form_submit_button("✨ Generate GTM Strategy")

    if submit_btn:
        with SessionLocal() as db:
            # 1. Save product
            target_mkt_list = [m.strip() for m in target_market.split(",") if m.strip()]
            geo_list = [g.strip() for g in geography.split(",") if g.strip()]

            product = db.query(Product).filter_by(name=name).first()
            if not product:
                product = Product(
                    name=name,
                    description=description,
                    target_market=target_mkt_list,
                    geography=geo_list,
                    price_range=price_range
                )
                db.add(product)
                db.commit()
                db.refresh(product)
            else:
                product.description = description
                product.target_market = target_mkt_list
                product.geography = geo_list
                product.price_range = price_range
                db.commit()

            # 2. Ensure accounts dataset is loaded
            re = ResearchEngine()
            re.load_accounts_from_csv(db)

            # 3. Generate ICP Profile
            icp_engine = ICPEngine()
            icp_profile = icp_engine.generate_icp_for_product(db, product)

            # 4. Score all target accounts
            scoring_engine = ScoringEngine()
            accounts = db.query(Account).all()
            for acc in accounts:
                scoring_engine.score_account(db, acc, product)

            st.success(f"✅ Generated ICP Strategy & scored {len(accounts)} target accounts for '{product.name}'!")

            # Display generated ICP Profile
            st.markdown("### 📋 Generated Ideal Customer Profile (ICP)")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.write("**Target Industries:**", ", ".join(icp_profile.industries or []))
                st.write("**Employee Range:**", f"{icp_profile.company_size_min} - {icp_profile.company_size_max} employees")
            with col_b:
                st.write("**Target Geographies:**", ", ".join(icp_profile.geographies or []))
                st.write("**Buyer Roles:**", ", ".join(icp_profile.buyer_roles or []))
            with col_c:
                st.write("**Required Tech Stack:**", ", ".join(icp_profile.technologies or []))
                st.write("**Exclusion Criteria:**", ", ".join(icp_profile.exclusions or []))

            with st.expander("See Key Pain Points & Buying Triggers"):
                st.write("**Pain Points Solved:**", icp_profile.pain_points)
                st.write("**Buying Triggers:**", icp_profile.buying_triggers)

    # Show existing products and ICPs if available
    with SessionLocal() as db:
        products = db.query(Product).all()
        if products:
            st.markdown("---")
            st.subheader("Existing Products in GTMOS")
            for prod in products:
                icp = db.query(ICPProfile).filter_by(product_id=prod.id).first()
                st.write(f"• **{prod.name}** (ID: {prod.id}) — ICP Status: {'✅ Generated' if icp else '⏳ Pending'}")

home = st.Page(home_page, title="Home", icon="🏠", default=True)
accounts = st.Page(str(current_dir / "accounts.py"), title="Accounts", icon="🏢")
signals = st.Page(str(current_dir / "signals.py"), title="Signals", icon="📡")
pipeline = st.Page(str(current_dir / "pipeline.py"), title="Review Queue", icon="📋")
analytics = st.Page(str(current_dir / "analytics.py"), title="Analytics", icon="📈")

pg = st.navigation([home, accounts, signals, pipeline, analytics])
pg.run()
