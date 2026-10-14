from app.db.database import SessionLocal
from app.models import Account, Score, Signal, Product
from app.services.research_engine import ResearchEngine
from app.services.scoring_engine import ScoringEngine

def main():
    db = SessionLocal()
    
    # Target Account
    acme = db.query(Account).filter_by(name="Acme Technologies").first()
    product = db.query(Product).first()
    
    # Get previous score
    score_before = db.query(Score).filter_by(account_id=acme.id, product_id=product.id).first()
    intent_before = score_before.intent_score if score_before else 0.0
    total_before = score_before.total_score if score_before else 0.0

    print("Running research engine...")
    # Clear signals to get fresh state
    db.query(Signal).delete()
    db.commit()
    
    re = ResearchEngine()
    re.extract_signals_from_csv(db)
    
    print("Rescoring accounts...")
    se = ScoringEngine()
    for acc in db.query(Account).all():
        se.score_account(db, acc, product)
        
    db.refresh(acme)
    score_after = db.query(Score).filter_by(account_id=acme.id, product_id=product.id).first()
    intent_after = score_after.intent_score if score_after else 0.0
    total_after = score_after.total_score if score_after else 0.0
    
    print("\n--- Acme Technologies Score Update ---")
    print(f"Total Score: {total_before} -> {total_after}")
    print(f"Intent Component: {intent_before} -> {intent_after}")
    
    print("\n--- Acme Technologies Evidence List ---")
    signals = db.query(Signal).filter_by(account_id=acme.id).all()
    if not signals:
        print("No signals found.")
    for sig in signals:
        print(f"Type: {sig.signal_type} | Strength: {sig.strength} | Source: {sig.source} | Date: {sig.detected_at.strftime('%Y-%m-%d')}")
        print(f"  Evidence: {sig.evidence}")
        print("-" * 50)
        
if __name__ == "__main__":
    main()
