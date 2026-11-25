"""Deterministic stand-in for LLM outreach drafting (mock mode only).

It reads the fields of GENERATE_DRAFT_PROMPT and writes a short draft that
quotes the strongest piece of evidence word for word, so the fact-check
guardrail sees only grounded claims.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

_EVIDENCE_RE = re.compile(r"^- \[(?P<type>[a-z_]+)\] .*?\(Evidence: '(?P<evidence>.*?)', Source: (?P<source>[^,]+),", re.M)

_OPENERS = {
    "support_hiring": "Saw that your team is scaling support",
    "funding": "Congrats on the new funding",
    "product_launch": "Noticed the recent launch",
    "international_expansion": "Saw the international expansion news",
    "executive_change": "Noticed the leadership change",
}


def _field(prompt: str, label: str) -> Optional[str]:
    for line in prompt.splitlines():
        if line.startswith(f"{label}:"):
            return line.split(":", 1)[1].strip()
    return None


def build_mock_draft(prompt: str) -> Dict[str, str]:
    account = _field(prompt, "Target Account") or "your team"
    persona = _field(prompt, "Target Persona") or "there"
    angle = _field(prompt, "Suggested Angle") or "team efficiency"
    match = _EVIDENCE_RE.search(prompt)

    if match:
        opener = _OPENERS.get(match.group("type"), "Saw some recent news")
        evidence = match.group("evidence").strip().rstrip(".")
        hook = f'{opener} ({match.group("source").strip()}: "{evidence}").'
        why = f"{account} fits the ICP and shows a verified {match.group('type').replace('_', ' ')} signal."
    else:
        hook = f"I've been looking at how teams like {account} handle support at scale."
        why = f"{account} fits the ICP on firmographics; no recent buying signal was verified."

    body = (
        "Hi there,\n\n"
        f"{hook} Teams at this stage usually feel it first in ticket backlog and response times.\n\n"
        f"We help with {angle}: resolving repetitive tickets automatically so the team can focus on the hard ones.\n\n"
        f"Open to a quick 15-minute call next week?"
    )
    return {"why_this_account": why, "message_draft": body}
