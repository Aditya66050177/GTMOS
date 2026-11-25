"""Deterministic, rule-based stand-in for LLM signal extraction (mock mode only).

It reads the research text one sentence at a time and quotes that sentence as
evidence, so evidence always appears word for word in the source. Sentences
that are negated, hedged or rumoured ("not hiring", "hiring freeze", "rumors
suggested") produce no signal: a mock should not be easier to fool than a
real analyst.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

NEGATION_CUES = (
    " not ", "n't ", " no ", "no plans", "freeze", "rumor", "rumour", "denied",
    "paused", "cancel", "layoff", "laid off", "halted", "postponed",
)

# (signal_type, description, strength, confidence, trigger phrases)
RULES: List[tuple] = [
    ("support_hiring", "Hiring support staff", 0.8, 0.9,
     ("hiring", "support staff", "support team", "support agents", "support reps")),
    ("funding", "Raised funding", 0.9, 0.9,
     ("raised", "funding round", "series a", "series b", "series c", "secured $", "investment from")),
    ("product_launch", "Launched new product", 0.7, 0.8,
     ("launched", "released a major", "unveiled", "new product")),
    ("international_expansion", "Expanding internationally", 0.8, 0.85,
     ("expand into", "expansion into", "new offices in", "international expansion",
      "regional headquarters", "europe", "asia", "emea", "apac")),
    ("executive_change", "New executive hire", 0.6, 0.8,
     ("hired a new chief", "appointed", "new chief", "new vp", "new head of")),
]

# support_hiring needs a support context, not any mention of hiring.
_SUPPORT_CONTEXT = ("support", "customer success", "help desk", "service team")


def _is_negated(sentence_lower: str) -> bool:
    padded = f" {sentence_lower} "
    return any(cue in padded for cue in NEGATION_CUES)


def _matches(rule_type: str, sentence_lower: str, triggers: tuple) -> bool:
    if not any(t in sentence_lower for t in triggers):
        return False
    if rule_type == "support_hiring":
        return any(c in sentence_lower for c in _SUPPORT_CONTEXT) and (
            "hiring" in sentence_lower or "expanding" in sentence_lower
        )
    return True


def extract_mock_signals(raw_text: str, source: str = "Research Note") -> List[Dict[str, Any]]:
    """Return schema-shaped signal dicts, each quoting its source sentence."""
    signals: List[Dict[str, Any]] = []
    seen_types: set = set()
    for sentence in _SENTENCE_SPLIT.split(raw_text.strip()):
        sentence = sentence.strip()
        lower = sentence.lower()
        if not sentence or _is_negated(lower):
            continue
        for rule_type, description, strength, confidence, triggers in RULES:
            if rule_type in seen_types or not _matches(rule_type, lower, triggers):
                continue
            seen_types.add(rule_type)
            signals.append({
                "type": rule_type,
                "description": description,
                "strength": strength,
                "source": source,
                "detected_at": "2026-01-01T00:00:00Z",
                "confidence": confidence,
                "evidence": sentence.rstrip("."),
            })
    return signals


def raw_text_from_prompt(prompt: str) -> str:
    """Pull the research text out of EXTRACT_SIGNALS_PROMPT, ignoring its instructions."""
    marker = "Raw Research Text:"
    if marker not in prompt:
        return prompt
    body = prompt.split(marker, 1)[1]
    return body.split("\nSource:", 1)[0].strip()
