"""
scripts/seed_activity.py
Simulates about 40 days of realistic GTM CRM activity with natural drop-off at each stage.
Uses a fixed random seed for reproducibility.
"""
import sys
import io
import random
from datetime import datetime, timedelta
from pathlib import Path

# Force UTF-8 stdout for Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Account, Product, Score, Signal, Contact, Activity, Opportunity, Draft
from app.services.research_engine import ResearchEngine
from app.services.scoring_engine import ScoringEngine
from app.services.crm_service import CRMService
from app.schemas.crm import PipelineStage

def seed_activity():
    random.seed(42)
    db = SessionLocal()

    print("=" * 70)
    print("[*] SEEDING 40-DAY REALISTIC GTM CRM & PIPELINE ACTIVITY")
    print("=" * 70)

    # 1. Ensure product and ICP exist
    product = db.query(Product).first()
    if not product:
        product = Product(
            name="AI Customer Support Assistant",
            description="Autonomous AI platform automating B2B customer support tickets.",
            target_market=["B2B SaaS", "Software"],
            geography=["US", "Canada"],
            price_range="$25,000"
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        from app.services.icp_engine import ICPEngine
        ICPEngine().generate_icp_for_product(db, product)

    # 2. Ensure accounts exist
    re = ResearchEngine()
    re.load_accounts_from_csv(db)
    re.extract_signals_from_csv(db)

    # 3. Ensure contacts are loaded
    crm = CRMService()
    contacts_loaded = crm.load_contacts_from_csv(db)
    print(f"  Loaded {contacts_loaded} contacts into CRM.")

    # 4. Score accounts
    se = ScoringEngine()
    accounts = db.query(Account).all()
    for acc in accounts:
        se.score_account(db, acc, product)

    # Fetch scored accounts sorted by total score
    scored_accounts = (
        db.query(Account, Score)
        .join(Score, (Account.id == Score.account_id) & (Score.product_id == product.id))
        .order_by(Score.total_score.desc())
        .all()
    )

    now = datetime.utcnow()
    total_activities = 0

    # Reset all accounts to Research first
    for acc, _ in scored_accounts:
        acc.stage = PipelineStage.RESEARCH.value

    db.query(Opportunity).delete()
    # Keep initial research activities, clear transient ones
    db.query(Activity).filter(Activity.activity_type.in_([
        "outreach_sent", "reply_received", "meeting_held", "opportunity_created", "deal_won", "deal_lost"
    ])).delete()
    db.commit()

    # Partition accounts by priority: higher scoring accounts advance further
    # Top 75 accounts get outreach
    contacted_pool = scored_accounts[:75]
    # 32 of them reply
    replied_pool = contacted_pool[:32]
    # 15 book a meeting
    meeting_pool = replied_pool[:15]
    # 7 convert to opportunity
    opp_pool = meeting_pool[:7]
    # 3 close won
    won_pool = opp_pool[:3]
    # 15 lost along the funnel
    lost_pool = contacted_pool[60:75]

    # Simulate Contacted
    for acc, sc in contacted_pool:
        days_ago = random.randint(15, 38)
        ts = now - timedelta(days=days_ago, hours=random.randint(1, 8))
        acc.stage = PipelineStage.CONTACTED.value
        db.add(Activity(
            account_id=acc.id,
            activity_type="outreach_sent",
            status="completed",
            timestamp=ts,
            activity_metadata={"channel": "email", "persona": "VP Customer Support"}
        ))
        total_activities += 1

    # Simulate Replied
    for acc, sc in replied_pool:
        days_ago = random.randint(10, 25)
        ts = now - timedelta(days=days_ago, hours=random.randint(1, 6))
        acc.stage = PipelineStage.REPLIED.value
        db.add(Activity(
            account_id=acc.id,
            activity_type="reply_received",
            status="completed",
            timestamp=ts,
            activity_metadata={"sentiment": "positive", "text": "Interested, let's chat next week."}
        ))
        total_activities += 1

    # Simulate Meeting
    for acc, sc in meeting_pool:
        days_ago = random.randint(5, 18)
        ts = now - timedelta(days=days_ago, hours=random.randint(2, 5))
        acc.stage = PipelineStage.MEETING.value
        db.add(Activity(
            account_id=acc.id,
            activity_type="meeting_held",
            status="completed",
            timestamp=ts,
            activity_metadata={"duration_mins": 30, "outcome": "qualified"}
        ))
        total_activities += 1

    # Simulate Opportunity
    for acc, sc in opp_pool:
        days_ago = random.randint(2, 12)
        ts = now - timedelta(days=days_ago)
        acc.stage = PipelineStage.OPPORTUNITY.value
        deal_val = random.choice([25000.0, 35000.0, 50000.0, 75000.0])
        db.add(Opportunity(
            account_id=acc.id,
            stage=PipelineStage.OPPORTUNITY.value,
            deal_value=deal_val,
            probability=0.6,
            created_at=ts
        ))
        db.add(Activity(
            account_id=acc.id,
            activity_type="opportunity_created",
            status="completed",
            timestamp=ts,
            activity_metadata={"deal_value": deal_val, "stage": "Opportunity"}
        ))
        total_activities += 1

    # Simulate Won
    for acc, sc in won_pool:
        days_ago = random.randint(1, 5)
        ts = now - timedelta(days=days_ago)
        acc.stage = PipelineStage.WON.value
        opp = db.query(Opportunity).filter_by(account_id=acc.id).first()
        if opp:
            opp.stage = PipelineStage.WON.value
            opp.probability = 1.0
            opp.closed_at = ts
        db.add(Activity(
            account_id=acc.id,
            activity_type="deal_won",
            status="completed",
            timestamp=ts,
            activity_metadata={"deal_value": opp.deal_value if opp else 45000.0, "stage": "Won"}
        ))
        total_activities += 1

    # Simulate Lost
    for acc, sc in lost_pool:
        days_ago = random.randint(1, 10)
        ts = now - timedelta(days=days_ago)
        acc.stage = PipelineStage.LOST.value
        db.add(Activity(
            account_id=acc.id,
            activity_type="deal_lost",
            status="completed",
            timestamp=ts,
            activity_metadata={"reason": "Competitor chosen / No budget"}
        ))
        total_activities += 1

    db.commit()

    # Stage summary
    counts = {}
    for stage in PipelineStage:
        cnt = db.query(Account).filter_by(stage=stage.value).count()
        counts[stage.value] = cnt

    print("\n[PIPELINE DISTRIBUTION AFTER 40-DAY SIMULATION]")
    for stg, c in counts.items():
        print(f"  {stg:<15}: {c} accounts")

    print(f"\n  Total Activities Logged: {total_activities}")
    print("\n" + "=" * 70)
    print("[SUCCESS] ACTIVITY SEEDING COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    seed_activity()
