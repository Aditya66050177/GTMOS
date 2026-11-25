# T5 follow-up — detecting lost sandbox edits

Branch `claude/modest-darwin-atz53w`, 2026-11-25. Not pushed, not deployed.

## Problem

Visitor edits in the public demo live in a per-browser sandbox held in one server
instance's memory and `/tmp`, for about two hours. They silently disappeared when:
- the sandbox expired (2-hour TTL),
- it was evicted (capacity cap of 200),
- a different Vercel instance answered (which has no sandbox for that browser), or
- it was recreated by a later edit after one of the above.

The visitor saw an approved draft quietly revert to pending, with no explanation
(pre-deployment review finding P1-1).

## Is reliable detection possible with the in-memory architecture?

**Yes, at the next request, for every scenario above.** The browser can remember *which*
sandbox holds its edits, and the server can say *which sandbox, if any*, answered each
request. Comparing the two detects every case where earlier edits are no longer the ones
being shown.

What it **cannot** do, and doesn't claim to:
- **Notice at the instant of loss.** Expiry or an instance switch is only discovered on the
  next API call. That happens on every page view, so in practice it is immediate.
- **Recover the lost edits.** They exist only in the old instance's memory. The fix is honest
  notification, not persistence (persistence would mean a database for visitor state, which
  was out of scope and would undo the "nothing is kept" property of the demo).
- **Detect a loss after browser storage is cleared.** Nothing is left to compare, but then
  the visitor has no record of the edits either. If storage is blocked entirely, tracking
  falls back to memory for the current page session.

## Design

**Server** (`app/api/public.py`):
- Every sandbox gets a random 16-hex token when it is created (`secrets.token_hex(8)`, not
  derived from the browser id). A sandbox recreated for the same browser gets a new token.
- `PublicDemoGuard` adds two headers to every guarded response, evaluated **after** the
  request ran:
  - `X-Demo-Sandbox: active | none`: whether this server holds a sandbox for the caller's
    `X-Demo-Session`.
  - `X-Demo-Sandbox-Id: <token>`: only when active.
- `SandboxRegistry.token(sid)` reads the token under the registry lock and applies expiry
  first, so an expired sandbox reports `none`.
- Nothing else changed: the write allowlist, rate limits, body cap, read-only shared data,
  offline LLM and reset scope are as before. The full local API (`app.api.main`) sends no
  such headers.

**Browser** (`web/src/lib/sandboxStatus.ts`, `web/src/lib/api.ts`, `AppShell.tsx`):
- After a response reports `active`, the client stores that token (`localStorage`, with a
  memory fallback).
- On every later guarded response:
  - **`none`** while a token is stored → **missing** (expired, evicted, or another server answered).
  - **A different token** → **recreated** (a new sandbox replaced the one holding the edits).
  - Either case shows the notice and updates or clears the stored token.
- An **intentional** reset through the app clears the stored token first, so it never
  triggers the notice.
- The notice is a persistent banner above every app page (`role="status"`,
  `aria-live="polite"`). It survives reloads (`sessionStorage`) until dismissed:

  > **Your earlier demo changes are no longer shown.** This server has no record of your
  > temporary sandbox. It may have expired (after about two hours), or a different server
  > answered this request. *(or: A new temporary sandbox was started for you because the
  > previous one expired or is held by a different server.)* Draft approvals, edits and
  > logged outreach from before are not shown anymore. They were never permanent: demo
  > changes live only in a temporary sandbox, nothing was sent, and shared demo data is
  > unaffected.

**Wording that no longer implies permanence:**
- The review queue description says approvals and logs are kept only in the temporary sandbox.
- "Logged as sent … in your temporary sandbox".
- "(kept in your temporary sandbox only)" beside the log button.

## Tests

### Backend: `tests/test_sandbox_status.py` (10 tests)
| Scenario | Expected and verified |
|---|---|
| No session header, or a fresh session id | `none`, no id |
| Edit | `active` with a 16-hex token; later reads (including routes with no database session) return the same token |
| Reset | The reset response itself reports `none`; later reads `none` |
| **Expired** (fake clock past the TTL) | `none`; the next edit is `active` with a **different** token |
| **Recreated** after reset and a new edit | Different token |
| **Evicted** at capacity | `none` |
| **Another server instance** (second independent public API) | `none` there; an edit there yields a different token |
| Isolation | One visitor never sees another's token; tokens aren't derived from the session id |
| Shared data | Template database file unchanged across edit, read and reset |
| Full local API | No sandbox headers |

### Browser (Playwright, production build plus real server with `DEMO_SANDBOX_TTL_SECONDS=8`)
| Scenario | Result |
|---|---|
| Browsing with no edits | No banner |
| Edit, then **Reset my sandbox** | No banner; stored token cleared |
| **Recreated**: edit, sandbox deleted behind the client's back, edit again | Banner with "new temporary sandbox" wording; tokens differ; Dismiss works |
| **Expired**: edit, wait 9 s past the 8 s TTL, open another page | Banner with "no record of your temporary sandbox" wording; **still shown after a full page reload**; 0 axe violations |
| **Different server instance**: edit, restart the API process (a new instance has no sandboxes), reload (390 px mobile) | Banner shown; no horizontal overflow |
| Console errors | 0 |

**Regression:** the T5 walkthrough suite and the T4 account-intelligence suite re-run
clean (0 errors, 0 axe violations; draft approval and rejection isolation unchanged).
Smoke test 15/15.

**Totals:** backend **357 passed**; frontend production build passes.

Screenshots: `docs/screenshots/t5/d-sandbox-expired.png`, `d-sandbox-recreated.png`,
`m-sandbox-other-instance.png`.

## Files changed

| File | Change |
|---|---|
| `app/api/public.py` | Per-sandbox random token; `SandboxRegistry.token()`; guard adds `X-Demo-Sandbox` and `X-Demo-Sandbox-Id` |
| `tests/test_sandbox_status.py` | New, 10 tests |
| `web/src/lib/sandboxStatus.ts` | New: detection and notice store |
| `web/src/lib/api.ts` | Calls `observeSandbox` on every response; reset is treated as intentional |
| `web/src/pages/AppShell.tsx` | Notice banner |
| `web/src/pages/Review.tsx` | Wording: the sandbox is temporary |
| `docs/FINAL_PRE_DEPLOYMENT_REVIEW.md` | P1-1 marked as addressed |

## Remaining limitations

1. **Loss is reported at the next request,** not proactively.
2. **Lost edits can't be restored.** Making them survive would need shared persistent
   storage for visitor state.
3. **Repeated instance switching** (A, B, A) shows the notice at each switch, because each
   instance holds a different sandbox. That's accurate, but can recur under heavy multi-instance
   load.
4. **No detection after browser storage is cleared;** there's nothing left to compare, and
   nothing the visitor remembers either.
5. **The headers reveal only whether this browser's own sandbox exists,** plus a random
   token. They expose no data, but they confirm that a guessed session id has a sandbox.
   Guessing a 128-bit id is infeasible.
