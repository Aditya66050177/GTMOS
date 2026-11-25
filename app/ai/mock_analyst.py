"""Deterministic stand-in for the LLM analyst's explanation step (mock mode only).

It reads the data block of ANALYST_EXPLAIN_PROMPT and restates numbers that are
already in it. It never computes a new figure, matching the live prompt's rule.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


def _parse(prompt: str) -> tuple[str, Dict[str, Any]]:
    func = ""
    for line in prompt.splitlines():
        if line.startswith("Function Executed:"):
            func = line.split(":", 1)[1].strip()
    raw = prompt.split("Data:", 1)[1].strip() if "Data:" in prompt else "{}"
    try:
        return func, json.loads(raw)
    except json.JSONDecodeError:
        return func, {}


def _best(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any] | None:
    rows = [r for r in rows if r.get("contacted")]
    return max(rows, key=lambda r: r.get(key, 0)) if rows else None


def build_mock_explanation(prompt: str) -> Dict[str, str]:
    func, data = _parse(prompt)
    return {"explanation": describe(func, data) + " (Numbers come straight from the analytics engine.)"}


def describe(func: str, data: Dict[str, Any]) -> str:
    """Deterministic one-paragraph description of an analytics result, using only its numbers."""

    if func == "get_funnel_summary" and "totals" in data:
        t = data["totals"]
        text = (f"Of {t['total_accounts']} accounts, {t['contacted']} were contacted, {t['replies']} replied, "
                f"{t['meetings']} reached a meeting, {t['opportunities']} became opportunities and {t['won']} closed won. "
                f"{t['lost']} were lost along the way.")
    elif func == "get_conversion_rates" and data.get("conversions"):
        convs = data["conversions"]
        worst = min(convs, key=lambda c: c["conversion_rate_pct"])
        parts = [f"{c['from_stage']}→{c['to_stage']} {c['conversion_rate_pct']}%" for c in convs]
        text = (f"Stage conversions: {', '.join(parts)}. The biggest drop-off is {worst['from_stage']} to "
                f"{worst['to_stage']} at {worst['conversion_rate_pct']}%.")
    elif func == "get_weekly_trends" and data.get("weekly_trends"):
        weeks = data["weekly_trends"]
        last = weeks[-1]
        peak = max(weeks, key=lambda w: w["contacted"])
        text = (f"Outreach peaked in {peak['week']} with {peak['contacted']} accounts contacted. In the latest week "
                f"({last['week']}) there were {last['replies']} replies and {last['meetings']} meetings.")
    elif func == "get_tier_performance" and data.get("performance_by_tier"):
        best = _best(data["performance_by_tier"], "win_rate_pct")
        text = (f"{best['tier']} converts best: {best['won']} won from {best['contacted']} contacted, a "
                f"{best['win_rate_pct']}% win rate across {best['accounts']} accounts." if best
                else "No tier has been contacted yet, so there is no conversion data.")
    elif func == "get_industry_performance" and data.get("performance_by_industry"):
        best = _best(data["performance_by_industry"], "replies")
        text = (f"{best['industry']} replies most: {best['replies']} replies from {best['contacted']} contacted, "
                f"with {best['meetings']} meetings and {best['won']} won." if best
                else "No industry has been contacted yet.")
    elif func == "get_angle_performance" and data.get("performance_by_angle"):
        best = _best(data["performance_by_angle"], "reply_rate_pct")
        text = (f"The '{best['angle']}' angle performs best with a {best['reply_rate_pct']}% reply rate "
                f"({best['replies']} replies from {best['contacted']} contacted)." if best
                else "No outreach angle has been used yet.")
    else:
        text = "This question can't be answered with the current analytics data."

    return text
