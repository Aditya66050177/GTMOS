"""Build the synthetic demo workspace used by scripts/demo.py and the public web app.

Every row is synthetic, clearly labeled demo data. Signal dates are anchored to
today so recency decay behaves the same whenever the demo is rebuilt.
"""
from __future__ import annotations

import contextlib
import io
import logging
import threading
from pathlib import Path

from app.db.database import Base, SessionLocal, engine
import app.models  # noqa: F401  (registers every table on Base.metadata)

logger = logging.getLogger(__name__)
_seed_lock = threading.Lock()

DEMO_PRODUCT = {
    "name": "AI Customer Support Assistant",
    "description": (
        "Autonomous AI platform that automates B2B customer support tickets, "
        "reducing resolution time and support costs for fast-growing SaaS companies."
    ),
    "target_market": ["B2B SaaS", "Software", "Cloud Services"],
    "geography": ["US", "Canada", "United States"],
    "price_range": "$25,000–$75,000/year",
}
DRAFTS_TO_SEED = 6

# Synthetic research notes added for the demo's fit-vs-intent comparison. Kept in a
# separate file so the baseline dataset (data/signals.csv) stays untouched; every
# row carries a "SYNTHETIC DEMO ADDITION" label that is stored with its provenance.
DEMO_ADDITIONS_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "signals_demo_additions.csv"
BASELINE_SIGNALS_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "signals.csv"


def reset_demo_database(quiet: bool = True, include_demo_additions: bool = True) -> dict:
    """Drop every table and rebuild the full demo workspace. Returns a short summary.

    include_demo_additions=False rebuilds the original baseline dataset only.
    """
    with _seed_lock:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink) if quiet else contextlib.nullcontext():
            return _build(include_demo_additions)


def ensure_demo_database() -> bool:
    """Seed only if the database has no product yet. Returns True if it seeded."""
    from app.models import Product

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(Product).first():
            return False
    with _seed_lock:
        with SessionLocal() as db:
            if db.query(Product).first():
                return False
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            _build(include_demo_additions=True)
    return True


def _build(include_demo_additions: bool = True) -> dict:
    from app.ai.llm import LLMService
    from app.models import Account, Draft, Product, Score
    from app.services.crm_service import CRMService
    from app.services.icp_engine import ICPEngine
    from app.services.personalization import PersonalizationEngine
    from app.services.research_engine import ResearchEngine
    from app.services.scoring_engine import ScoringEngine

    with SessionLocal() as db:
        product = Product(**DEMO_PRODUCT)
        db.add(product)
        db.commit()
        db.refresh(product)

        ICPEngine(llm_service=LLMService(mode="mock")).generate_icp_for_product(db, product)

        research = ResearchEngine(llm_service=LLMService(mode="mock"))
        research.load_accounts_from_csv(db)
        from app.services.research_engine import anchor_shift, read_notes
        shift = anchor_shift(read_notes(BASELINE_SIGNALS_CSV))
        research.extract_signals_from_csv(db, BASELINE_SIGNALS_CSV, shift=shift, dataset="baseline")
        if include_demo_additions and DEMO_ADDITIONS_CSV.exists():
            research.extract_signals_from_csv(db, DEMO_ADDITIONS_CSV, shift=shift, dataset="demo_addition")

        scorer = ScoringEngine()
        for account in db.query(Account).all():
            scorer.score_account(db, account, product)
        product_id = product.id

    # seed_activity opens its own session and replays ~40 days of pipeline history.
    from scripts.seed_activity import seed_activity
    seed_activity()

    with SessionLocal() as db:
        CRMService().load_contacts_from_csv(db)
        drafts = _seed_review_queue(db, product_id, PersonalizationEngine(llm=LLMService(mode="mock")))
        accounts = db.query(Account).count()
        scores = db.query(Score).filter_by(product_id=product_id).count()

    return {"accounts": accounts, "scores": scores, "drafts": drafts,
            "dataset": "baseline + demo additions" if include_demo_additions else "baseline"}


def _seed_review_queue(db, product_id: int, engine_: "object") -> int:
    """Draft outreach for the top actionable accounts early in the funnel, so the queue has work."""
    from app.models import Account, Score

    candidates = (
        db.query(Account)
        .join(Score, (Score.account_id == Account.id) & (Score.product_id == product_id))
        .filter(Account.stage.in_(["Research", "Contacted"]))
        .order_by(Score.total_score.desc())
        .limit(DRAFTS_TO_SEED * 3)
        .all()
    )
    created = 0
    for account in candidates:
        if created >= DRAFTS_TO_SEED:
            break
        try:
            engine_.generate_draft(db, account.id, product_id=product_id)
            created += 1
        except ValueError as exc:  # deprioritized or guardrail-rejected: skip, never force
            logger.info("Skipped draft for %s: %s", account.name, exc)
    return created
