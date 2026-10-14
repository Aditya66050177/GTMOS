"""
scripts/verify_funnel.py
Verifies that AnalyticsEngine, direct SQL, and the FastAPI /analytics/funnel
endpoint all report matching stage counts and funnel totals.
Windows-safe: no emojis.
"""
import sys
import io
import json
from pathlib import Path

# Force UTF-8 stdout for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.analytics_engine import AnalyticsEngine
from app.models import Account


def run_seed():
    """Run the seed script to ensure fresh data exists."""
    print(">>> Re-running seed_activity.py ...")
    import scripts.seed_activity as sa
    sa.seed_activity()
    print()


def verify_funnel():
    init_db()
    run_seed()

    db = SessionLocal()
    engine = AnalyticsEngine()

    # -----------------------------------------------------------------------
    # 1. Analytics Engine
    # -----------------------------------------------------------------------
    print("=" * 60)
    print("SOURCE 1: AnalyticsEngine.get_funnel_analytics()")
    print("=" * 60)
    ae_result = engine.get_funnel_analytics(db)
    t = ae_result.totals
    print(f"  total_accounts : {t.total_accounts}")
    print(f"  high_priority  : {t.high_priority_accounts}")
    print(f"  contacted      : {t.contacted}")
    print(f"  replies        : {t.replies}")
    print(f"  meetings       : {t.meetings}")
    print(f"  opportunities  : {t.opportunities}")
    print(f"  won            : {t.won}")
    print(f"  lost           : {t.lost}")
    print()
    print("  Stage Counts (AnalyticsEngine):")
    for stage, cnt in sorted(ae_result.stage_counts.items()):
        print(f"    {stage:<15}: {cnt}")
    print()
    print("  Stage-to-Stage Conversions:")
    for c in ae_result.conversions:
        print(f"    {c.from_stage} -> {c.to_stage}: {c.from_count} -> {c.to_count} ({c.conversion_rate_pct}%)")

    # -----------------------------------------------------------------------
    # 2. Direct SQL
    # -----------------------------------------------------------------------
    print()
    print("=" * 60)
    print("SOURCE 2: Direct SQL  (SELECT stage, COUNT(*) FROM accounts GROUP BY stage)")
    print("=" * 60)
    from sqlalchemy import text
    rows = db.execute(text("SELECT stage, COUNT(*) as cnt FROM accounts GROUP BY stage")).fetchall()
    sql_stage_counts = {}
    for row in rows:
        stage_val = row[0] or "Research"
        cnt = row[1]
        sql_stage_counts[stage_val] = cnt
        print(f"  {stage_val:<15}: {cnt}")
    print()

    # -----------------------------------------------------------------------
    # 3. FastAPI TestClient
    # -----------------------------------------------------------------------
    print("=" * 60)
    print("SOURCE 3: FastAPI /analytics/funnel (TestClient)")
    print("=" * 60)
    try:
        from fastapi.testclient import TestClient
        from app.api.main import app
        client = TestClient(app)
        response = client.get("/analytics/funnel")
        if response.status_code == 200:
            api_data = response.json()
            api_totals = api_data.get("totals", {})
            api_stage_counts = api_data.get("stage_counts", {})
            print(f"  HTTP Status      : {response.status_code}")
            print(f"  total_accounts   : {api_totals.get('total_accounts')}")
            print(f"  contacted        : {api_totals.get('contacted')}")
            print(f"  replies          : {api_totals.get('replies')}")
            print(f"  meetings         : {api_totals.get('meetings')}")
            print(f"  won              : {api_totals.get('won')}")
            print(f"  lost             : {api_totals.get('lost')}")
            print()
            print("  Stage Counts (API):")
            for stage, cnt in sorted(api_stage_counts.items()):
                print(f"    {stage:<15}: {cnt}")
        else:
            print(f"  [ERROR] HTTP {response.status_code}: {response.text[:200]}")
            api_totals = {}
            api_stage_counts = {}
    except Exception as exc:
        print(f"  [ERROR] Could not call API: {exc}")
        api_totals = {}
        api_stage_counts = {}

    # -----------------------------------------------------------------------
    # 4. Cross-check
    # -----------------------------------------------------------------------
    print()
    print("=" * 60)
    print("CROSS-CHECK")
    print("=" * 60)

    # Stage counts: AnalyticsEngine vs Direct SQL
    all_stages = set(list(ae_result.stage_counts.keys()) + list(sql_stage_counts.keys()))
    mismatches = []
    for s in sorted(all_stages):
        ae_cnt = ae_result.stage_counts.get(s, 0)
        sql_cnt = sql_stage_counts.get(s, 0)
        match = "OK" if ae_cnt == sql_cnt else "MISMATCH"
        if match == "MISMATCH":
            mismatches.append(s)
        print(f"  {s:<15}: AnalyticsEngine={ae_cnt}  SQL={sql_cnt}  [{match}]")

    if mismatches:
        print(f"\n  [WARN] Stage count mismatches in: {mismatches}")
    else:
        print("\n  All stage counts match between AnalyticsEngine and SQL. [PASS]")

    # Totals: AnalyticsEngine vs API
    if api_totals:
        total_match = ae_result.totals.total_accounts == api_totals.get("total_accounts")
        won_match = ae_result.totals.won == api_totals.get("won")
        if total_match and won_match:
            print("  AnalyticsEngine totals match API response. [PASS]")
        else:
            print(f"  [WARN] Totals diverge: AE total={ae_result.totals.total_accounts} API={api_totals.get('total_accounts')}")
            print(f"         AE won={ae_result.totals.won} API={api_totals.get('won')}")

    db.close()
    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    verify_funnel()
