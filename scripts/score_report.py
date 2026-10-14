"""
scripts/score_report.py
Run score-all on the 150 demo accounts and print:
  - Tier distribution
  - Top 10 and Bottom 5 accounts
  - Acme Technologies score
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import Counter
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.models import Product, Account, ICPProfile, Score
from app.services.icp_engine import ICPEngine
from app.services.research_engine import ResearchEngine
from app.services.scoring_engine import ScoringEngine

def main():
    init_db()
    db = SessionLocal()

    # Ensure we have a product + ICP
    product = db.query(Product).filter_by(name="AI Customer Support Assistant").first()
    if not product:
        product = Product(
            name="AI Customer Support Assistant",
            description="Autonomous AI agent platform for automating B2B customer support tickets, "
                        "resolving repetitive help desk overload, and improving response times.",
            target_market=["B2B SaaS", "Software"],
            geography=["US", "United States"],
            price_range="$10,000 - $50,000",
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        print(f"Created product: {product.name} (id={product.id})")

    icp = db.query(ICPProfile).filter_by(product_id=product.id).first()
    if not icp:
        icp_engine = ICPEngine()
        icp_engine.generate_icp_for_product(db, product)
        print("Generated ICP profile.")

    # Load accounts if needed
    if db.query(Account).count() < 150:
        re = ResearchEngine()
        n = re.load_accounts_from_csv(db)
        print(f"Loaded {n} accounts from CSV.")
        n_sigs = re.extract_signals_from_csv(db)
        print(f"Extracted {n_sigs} signals from research.")

    # Score all
    se = ScoringEngine()
    accounts = db.query(Account).all()
    for acc in accounts:
        se.score_account(db, acc, product)
    print(f"\nScored {len(accounts)} accounts.\n")

    # Fetch results
    rows = (
        db.query(Account, Score)
        .join(Score, (Account.id == Score.account_id) & (Score.product_id == product.id))
        .all()
    )
    rows_sorted = sorted(rows, key=lambda x: x[1].total_score, reverse=True)

    # Tier distribution
    tier_counts = Counter(sc.tier for _, sc in rows_sorted)
    print("=" * 60)
    print("TIER DISTRIBUTION")
    print("=" * 60)
    tier_order = ["Priority 1", "Priority 2", "Priority 3", "Low"]
    total = sum(tier_counts.values())
    for t in tier_order:
        c = tier_counts.get(t, 0)
        pct = 100 * c / total if total else 0
        print(f"  {t:<15}: {c:>4} accounts ({pct:.1f}%)")

    # Top 10
    print("\n" + "=" * 60)
    print("TOP 10 ACCOUNTS")
    print("=" * 60)
    print(f"{'Rank':<5} {'Company':<30} {'Score':>6} {'Tier':<15}")
    print("-" * 60)
    for rank, (acc, sc) in enumerate(rows_sorted[:10], 1):
        print(f"{rank:<5} {acc.name:<30} {sc.total_score:>6.1f} {sc.tier:<15}")

    # Bottom 5
    print("\n" + "=" * 60)
    print("BOTTOM 5 ACCOUNTS")
    print("=" * 60)
    print(f"{'Rank':<5} {'Company':<30} {'Score':>6} {'Tier':<15}")
    print("-" * 60)
    for rank, (acc, sc) in enumerate(rows_sorted[-5:], len(rows_sorted) - 4):
        print(f"{rank:<5} {acc.name:<30} {sc.total_score:>6.1f} {sc.tier:<15}")

    # Acme Technologies
    print("\n" + "=" * 60)
    print("ACME TECHNOLOGIES (benchmark target: ~87)")
    print("=" * 60)
    acme_row = next(((a, s) for a, s in rows_sorted if a.name == "Acme Technologies"), None)
    if acme_row:
        a, s = acme_row
        rank_pos = next(i+1 for i, (acc, _) in enumerate(rows_sorted) if acc.name == "Acme Technologies")
        print(f"  Rank: #{rank_pos}")
        print(f"  Total Score : {s.total_score}")
        print(f"  Tier        : {s.tier}")
        print(f"  ICP Fit     : {s.icp_fit} / 30")
        print(f"  Company Fit : {s.company_fit} / 20")
        print(f"  Tech Fit    : {s.technology_fit} / 15")
        print(f"  Intent      : {s.intent_score} / 20")
        print(f"  Geography   : {s.geography_score} / 15")
    else:
        print("  Acme Technologies not found in results!")

    db.close()

if __name__ == "__main__":
    main()
