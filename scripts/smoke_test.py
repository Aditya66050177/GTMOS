"""Deployment smoke test for the public GTMOS demo. Standard library only.

Checks the API is up, the pages' data endpoints answer, the public safeguards
are active, and a visitor's edit stays in their own sandbox.

Usage (PowerShell, from the project root):
    python scripts/smoke_test.py http://127.0.0.1:8000          # local: uvicorn api.index:app
    python scripts/smoke_test.py https://<your-app>.vercel.app   # after deploying
    python scripts/smoke_test.py https://<your-app>.vercel.app --frontend   # also fetch the site

Exits non-zero if any check fails.
"""
import argparse
import json
import secrets
import sys
import urllib.error
import urllib.request
from typing import Optional, Tuple

TIMEOUT = 30


def call(base: str, method: str, path: str, body: Optional[object] = None,
         session: Optional[str] = None, raw: Optional[bytes] = None) -> Tuple[int, object]:
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "gtmos-smoke-test")
    if session:
        req.add_header("X-Demo-Session", session)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            text = res.read().decode()
            status = res.status
    except urllib.error.HTTPError as err:
        text, status = err.read().decode(), err.code
    try:
        return status, json.loads(text)
    except json.JSONDecodeError:
        return status, text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--frontend", action="store_true", help="also check the HTML site and an SPA route")
    args = parser.parse_args()
    base, sid = args.base_url, secrets.token_hex(16)
    results = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{'  — ' + detail if detail and not ok else ''}")

    status, body = call(base, "GET", "/api/health")
    check("health is healthy", status == 200 and isinstance(body, dict) and body.get("status") == "healthy", f"{status} {body}")

    status, overview = call(base, "GET", "/api/web/overview")
    check("overview has 150 accounts", status == 200 and overview.get("counts", {}).get("accounts") == 150, f"{status}")
    check("public LLM is offline mock", isinstance(overview, dict) and overview.get("llm_mode") == "mock", str(overview.get("llm_mode") if isinstance(overview, dict) else overview))

    status, accounts = call(base, "GET", "/api/web/accounts")
    check("accounts list", status == 200 and isinstance(accounts, list) and len(accounts) == 150, f"{status}")
    acme = next((a for a in accounts if a.get("name") == "Acme Technologies"), None) if isinstance(accounts, list) else None
    check("Acme rumour test still holds (69.5, Priority 3)", bool(acme) and acme["total_score"] == 69.5 and acme["tier"] == "Priority 3", str(acme))

    if isinstance(accounts, list) and accounts:
        status, detail = call(base, "GET", f"/api/web/accounts/{accounts[0]['id']}")
        check("account detail with score breakdown", status == 200 and bool(detail.get("score")), f"{status}")

    status, play = call(base, "POST", "/api/web/playground", {
        "industry": "B2B SaaS", "employee_count": 200, "country": "US",
        "research_note": "We are hiring 20 new support agents."})
    check("playground scores", status == 200 and "score" in play, f"{status} {play}")

    status, _ = call(base, "POST", "/api/accounts/1/contacts", {"name": "x"}, session=sid)
    check("write routes are blocked (403)", status == 403, str(status))

    status, _ = call(base, "PATCH", "/api/drafts/1", session=sid, raw=b'{"body":"' + b"a" * 20_000 + b'"}')
    check("oversized body rejected (413)", status == 413, str(status))

    status, _ = call(base, "POST", "/api/drafts/1/approve")
    check("edits need a demo session (400)", status == 400, str(status))

    status, drafts = call(base, "GET", "/api/web/drafts")
    pending = [d for d in drafts if d.get("status") == "pending"] if isinstance(drafts, list) else []
    check("review queue has pending drafts", status == 200 and bool(pending), f"{status}")
    if pending:
        draft_id = pending[0]["id"]
        status, _ = call(base, "POST", f"/api/drafts/{draft_id}/approve", session=sid)
        _, mine = call(base, "GET", f"/api/drafts/{draft_id}", session=sid)
        _, shared = call(base, "GET", f"/api/drafts/{draft_id}")
        # On Vercel a follow-up request can land on another instance without this sandbox.
        check("approval stays in the visitor's sandbox", status == 200 and shared.get("status") == "pending",
              f"approve={status} mine={mine.get('status') if isinstance(mine, dict) else mine} shared={shared}")
        status, reset = call(base, "POST", "/api/web/reset", session=sid)
        check("reset discards only this sandbox", status == 200 and reset.get("status") == "reset", f"{status} {reset}")

    if args.frontend:
        for path in ("/", "/app/accounts"):
            req = urllib.request.Request(base.rstrip("/") + path, headers={"User-Agent": "gtmos-smoke-test"})
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
                    html = res.read().decode()
                check(f"site serves {path}", res.status == 200 and '<div id="root">' in html, str(res.status))
            except urllib.error.HTTPError as err:
                check(f"site serves {path}", False, str(err.code))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed against {base}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
