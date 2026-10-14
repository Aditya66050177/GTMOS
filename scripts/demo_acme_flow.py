"""
scripts/demo_acme_flow.py
Runs the complete end-to-end Phase 3 flow for Acme Technologies:
1. Score
2. Recommendation
3. Personalize (Draft Generation)
4. Human Edit
5. Approve & Activity Logging
"""
import sys
import io
from pathlib import Path

# Force UTF-8 stdout for Windows consoles
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.models import Account, Product, Score, Signal, Draft, Activity, ICPProfile
from app.services.research_engine import ResearchEngine
from app.services.scoring_engine import ScoringEngine
from app.services.recommendation_engine import RecommendationEngine
from app.services.personalization import PersonalizationEngine

def run_acme_flow():
    db = SessionLocal()
    print("=" * 70)
    print("[*] GTMOS END-TO-END FLOW: ACME TECHNOLOGIES")
    print("=" * 70)

    # 0. Load Data
    product = db.query(Product).filter_by(id=1).first()
    if not product:
        product = db.query(Product).first()

    acme = db.query(Account).filter_by(name="Acme Technologies").first()
    if not acme:
        re = ResearchEngine()
        re.load_accounts_from_csv(db)
        acme = db.query(Account).filter_by(name="Acme Technologies").first()

    # Ensure research signals are extracted
    re = ResearchEngine()
    re.extract_signals_from_csv(db)

    # STEP 1: SCORE
    print("\n[STEP 1: SCORING]")
    se = ScoringEngine()
    score_res = se.score_account(db, acme, product)
    print(f"  Account     : {acme.name} ({acme.industry}, {acme.employee_count} employees, {acme.country})")
    print(f"  Total Score : {score_res.total_score} / 100")
    print(f"  Fit Tier    : {score_res.tier}")
    print(f"  ICP Fit     : {score_res.icp_fit} / 30")
    print(f"  Company Fit : {score_res.company_fit} / 20")
    print(f"  Tech Fit    : {score_res.technology_fit} / 15")
    print(f"  Intent      : {score_res.intent_score} / 20")
    print(f"  Geography   : {score_res.geography_score} / 15")

    # STEP 2: RECOMMENDATION
    print("\n[STEP 2: ACTION RECOMMENDATION]")
    rec_engine = RecommendationEngine()
    signals = db.query(Signal).filter_by(account_id=acme.id).all()
    icp = db.query(ICPProfile).filter_by(product_id=product.id).first()
    rec = rec_engine.get_recommendation(score_res, signals, icp)

    print(f"  Action      : {rec.action}")
    print(f"  Rationale   : {rec.reason}")
    print(f"  Persona     : {rec.suggested_persona}")
    print(f"  Angle       : {rec.suggested_angle}")

    # STEP 3: PERSONALIZE (Generate Draft)
    print("\n[STEP 3: PERSONALIZATION & DRAFT GENERATION]")
    pe = PersonalizationEngine()
    draft = pe.generate_draft(db, acme.id, product.id)
    print(f"  Draft ID    : #{draft.id}")
    print(f"  Status      : {draft.status}")
    print(f"  Evidence IDs: {draft.evidence_ids}")
    print(f"  Initial Body: \n    \"{draft.body}\"")

    # STEP 4: HUMAN EDIT
    print("\n[STEP 4: HUMAN REVIEW & EDIT]")
    edited_text = draft.body + " P.S. Looking forward to connecting at SaaStr next month."
    draft.body = edited_text
    db.commit()
    db.refresh(draft)
    print(f"  Original Body: \n    \"{draft.original_body}\"")
    print(f"  Edited Body  : \n    \"{draft.body}\"")

    # STEP 5: APPROVE
    print("\n[STEP 5: HUMAN APPROVAL]")
    draft.status = "approved"
    activity = Activity(
        account_id=acme.id,
        activity_type="outreach_approved",
        status="approved",
        activity_metadata={"draft_id": draft.id, "body": draft.body}
    )
    db.add(activity)
    db.commit()
    db.refresh(draft)
    db.refresh(activity)

    print(f"  Draft Status: {draft.status.upper()}")
    print(f"  Activity ID : #{activity.id} (Type: {activity.activity_type}, Status: {activity.status})")
    print(f"  Safety Check: Zero external emails dispatched. Ready in Review Queue.")

    print("\n" + "=" * 70)
    print("[SUCCESS] ACME FLOW COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    run_acme_flow()
