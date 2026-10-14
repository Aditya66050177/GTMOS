"""
scripts/demo.py
GTMOS End-to-End Demo Runner.

Resets the SQLite database, loads data, runs research and scoring,
seeds the pipeline, and prints a summary.

Usage:
    python scripts/demo.py
"""
import sys
import io
import os
import time
import logging
from pathlib import Path

# Silence non-critical logger output on stdout/stderr
logging.basicConfig(level=logging.ERROR)
logging.getLogger("app").setLevel(logging.ERROR)

# Windows-safe stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _separator(title: str):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    _separator("GTMOS DEMO — FULL END-TO-END RUN")

    # ── Step 1: Reset database ─────────────────────────────────────────
    print("\n[1/8] Resetting database...")
    db_path = ROOT / "gtmos.db"
    if db_path.exists():
        os.remove(db_path)
        print(f"  Removed {db_path}")

    from app.db.init_db import init_db
    init_db()
    print("  Database initialized.")

    from app.db.database import SessionLocal
    from app.models import Account, Product, Score, ICPProfile
    db = SessionLocal()

    # ── Step 2: Create product ─────────────────────────────────────────
    print("\n[2/8] Creating product...")
    from app.models.models import Product as ProductModel
    product = ProductModel(
        name="AI Customer Support Assistant",
        description="Autonomous AI platform that automates B2B customer support tickets, "
                    "reducing resolution time and support costs for fast-growing SaaS companies.",
        target_market=["B2B SaaS", "Software", "Cloud Services"],
        geography=["US", "Canada", "United States"],
        price_range="$25,000–$75,000/year",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    print(f"  Product created: '{product.name}' (id={product.id})")

    # ── Step 3: Generate ICP ──────────────────────────────────────────
    print("\n[3/8] Generating ICP (mock mode)...")
    from app.services.icp_engine import ICPEngine
    from app.ai.llm import LLMService
    icp_engine = ICPEngine(llm_service=LLMService(mode="mock"))
    icp = icp_engine.generate_icp_for_product(db, product)
    print(f"  ICP generated: industries={icp.industries[:2]}, "
          f"size={icp.company_size_min}-{icp.company_size_max} employees")

    # ── Step 4: Load accounts ─────────────────────────────────────────
    print("\n[4/8] Loading 150 accounts from data/accounts.csv...")
    from app.services.research_engine import ResearchEngine
    re = ResearchEngine()
    n_accounts = re.load_accounts_from_csv(db)
    print(f"  Loaded {db.query(Account).count()} accounts.")

    # ── Step 5: Extract signals ───────────────────────────────────────
    print("\n[5/8] Extracting signals from data/signals.csv...")
    n_signals = re.extract_signals_from_csv(db)
    print(f"  Signal extraction complete.")

    # ── Step 6: Score all accounts ────────────────────────────────────
    print("\n[6/8] Scoring all accounts...")
    from app.services.scoring_engine import ScoringEngine
    se = ScoringEngine()
    accounts = db.query(Account).all()
    t0 = time.time()
    for acc in accounts:
        se.score_account(db, acc, product)
    elapsed = time.time() - t0
    print(f"  Scored {len(accounts)} accounts in {elapsed:.1f}s.")

    # ── Step 7: Seed pipeline activity ───────────────────────────────
    print("\n[7/8] Seeding 40-day pipeline simulation (seed=42)...")
    db.close()  # seed_activity opens its own session
    from scripts.seed_activity import seed_activity
    seed_activity()
    db = SessionLocal()

    # ── Step 8: Load contacts ─────────────────────────────────────────
    print("\n[8/8] Loading contacts from data/contacts.csv...")
    from app.services.crm_service import CRMService
    crm = CRMService()
    n_contacts = crm.load_contacts_from_csv(db)
    print(f"  Loaded {n_contacts} contacts.")

    # ── Summary ───────────────────────────────────────────────────────
    _separator("DEMO SUMMARY")

    # Tier distribution
    from app.models.models import Score as ScoreModel
    product = db.query(ProductModel).first()
    product_id = product.id if product else 1
    scores = db.query(ScoreModel).filter_by(product_id=product_id).all()
    tier_dist = {}
    for s in scores:
        tier_dist[s.tier] = tier_dist.get(s.tier, 0) + 1
    print("\nTier Distribution:")
    for tier in ["Priority 1", "Priority 2", "Priority 3", "Low"]:
        count = tier_dist.get(tier, 0)
        bar = "#" * count
        print(f"  {tier:<15}: {count:>3}  {bar}")

    # Top 5 accounts
    top5 = (
        db.query(Account, ScoreModel)
        .join(ScoreModel, (Account.id == ScoreModel.account_id) & (ScoreModel.product_id == product_id))
        .order_by(ScoreModel.total_score.desc())
        .limit(5)
        .all()
    )
    print("\nTop 5 Accounts:")
    print(f"  {'Rank':<5} {'Name':<35} {'Score':<8} {'Tier'}")
    print(f"  {'-'*5} {'-'*35} {'-'*8} {'-'*15}")
    for i, (acc, sc) in enumerate(top5, 1):
        print(f"  {i:<5} {acc.name:<35} {sc.total_score:<8.1f} {sc.tier}")

    # Acme score breakdown
    acme = db.query(Account).filter(Account.name.ilike("%acme%")).first()
    if acme:
        acme_score = db.query(ScoreModel).filter_by(account_id=acme.id, product_id=product_id).first()
        if acme_score:
            print(f"\nAcme Technologies Score Breakdown:")
            print(f"  Total Score  : {acme_score.total_score:.1f}")
            print(f"  Tier         : {acme_score.tier}")
            print(f"  ICP Fit      : {acme_score.icp_fit:.1f} / 30")
            print(f"  Company Fit  : {acme_score.company_fit:.1f} / 20")
            print(f"  Tech Fit     : {acme_score.technology_fit:.1f} / 15")
            print(f"  Intent Score : {acme_score.intent_score:.1f} / 20")
            print(f"  Geography    : {acme_score.geography_score:.1f} / 15")

    # Pipeline stage distribution
    from app.schemas.crm import PipelineStage
    print("\nPipeline Stage Distribution:")
    for stage in PipelineStage:
        count = db.query(Account).filter_by(stage=stage.value).count()
        if count > 0:
            print(f"  {stage.value:<15}: {count}")

    db.close()
    _separator("DEMO COMPLETE")
    print("\nNext steps:")
    print("  1. Start backend : .venv\\Scripts\\uvicorn app.api.main:app --port 8000")
    print("  2. Start dashboard: .venv\\Scripts\\streamlit run app/dashboard/home.py")
    print("  3. Run evaluation : python -m app.ai.run_eval --mode mock")
    print()


if __name__ == "__main__":
    main()
