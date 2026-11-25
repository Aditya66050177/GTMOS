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
    " not ", "n't ", " no ", "no plans", "freeze", "frozen", "rumor", "rumour", "denied",
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


# Cues that explicitly contradict a claim (a stated "no").
_NEGATED_CUES = (" not ", "n't ", " no ", "no plans", "freeze", "frozen", "denied", "paused", "cancel",
                 "layoff", "laid off", "halted", "postponed")
# Cues that mark a claim as hearsay rather than a confirmed fact. Only cues that
# NEGATION_CUES also rejects belong here; this list labels rejections, it never
# decides them. ("reportedly" is NOT rejected by the extractor: a known gap.)
_UNSUPPORTED_CUES = ("rumor", "rumour")
# Hedges: the sentence talks about a topic without committing to anything.
_HEDGE_CUES = ("might", " may ", "could", "looking into", "considering", "exploring", "possibly", "perhaps")
# Broad topic words, used only to decide whether a skipped sentence was a claim at all.
_TOPICS = (
    ("support_hiring", ("hiring", "hire", "recruit", "headcount")),
    ("funding", ("fund", "raise", "raising", "series", "investment", "investor")),
    ("product_launch", ("launch", "release", "unveil")),
    ("international_expansion", ("expand", "expansion", "international", "global", "new office")),
    ("executive_change", ("ceo", "cro", "chief", "vp ", "appoint")),
    ("rapid_growth", ("growth", "grow", "scaling", "scale")),
)


def _is_negated(sentence_lower: str) -> bool:
    padded = f" {sentence_lower} "
    return any(cue in padded for cue in NEGATION_CUES)


def _found(cues: tuple, sentence_lower: str) -> List[str]:
    padded = f" {sentence_lower} "
    return [c.strip() for c in cues if c in padded]


def _topic(sentence_lower: str) -> str | None:
    for topic, words in _TOPICS:
        if any(w in sentence_lower for w in words):
            return topic
    return None


def _classify_skipped(sentence: str, lower: str) -> Dict[str, Any] | None:
    """Explain why a sentence that NEGATION_CUES excluded is not a signal.

    The accept/reject decision itself is unchanged (it is `_is_negated`); this only
    names the reason so the rejection can be stored instead of silently dropped.
    """
    negated, hearsay = _found(_NEGATED_CUES, lower), _found(_UNSUPPORTED_CUES, lower)
    if negated:
        reason = f"Contradicted by: {', '.join(repr(c) for c in negated)}"
        if hearsay:
            reason = f"Hearsay ({', '.join(repr(c) for c in hearsay)}) contradicted by: {', '.join(repr(c) for c in negated)}"
        category = "negated"
    else:
        category = "unsupported"
        reason = f"Hearsay, not a confirmed fact: {', '.join(repr(c) for c in hearsay)}"
    return {"sentence": sentence.rstrip("."), "category": category, "reason": reason,
            "claimed_type": _topic(lower), "cues": negated + hearsay}


def _matches(rule_type: str, sentence_lower: str, triggers: tuple) -> bool:
    if not any(t in sentence_lower for t in triggers):
        return False
    if rule_type == "support_hiring":
        return any(c in sentence_lower for c in _SUPPORT_CONTEXT) and (
            "hiring" in sentence_lower or "expanding" in sentence_lower
        )
    return True


def analyze_note(raw_text: str, source: str = "Research Note") -> Dict[str, List[Dict[str, Any]]]:
    """Split a research note into accepted signals and rejected claims.

    Accepted signals quote their sentence. Rejected claims are sentences that talk
    about a buying-signal topic but are negated, hearsay, or hedged ("ambiguous").
    Sentences with no signal topic at all are not claims and are not recorded.
    """
    signals: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    seen_types: set = set()
    for sentence in _SENTENCE_SPLIT.split(raw_text.strip()):
        sentence = sentence.strip()
        lower = sentence.lower()
        if not sentence:
            continue
        if _is_negated(lower):
            rejected.append(_classify_skipped(sentence, lower))
            continue
        matched_any = False
        for rule_type, description, strength, confidence, triggers in RULES:
            if not _matches(rule_type, lower, triggers):
                continue
            matched_any = True
            if rule_type in seen_types:
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
        hedges, topic = _found(_HEDGE_CUES, lower), _topic(lower)
        if not matched_any and topic and hedges:
            rejected.append({
                "sentence": sentence.rstrip("."), "category": "ambiguous",
                "reason": f"Speculative wording ({', '.join(repr(h) for h in hedges)}); no concrete event stated",
                "claimed_type": topic, "cues": hedges,
            })
    return {"signals": signals, "rejected": rejected}


def extract_mock_signals(raw_text: str, source: str = "Research Note") -> List[Dict[str, Any]]:
    """Return schema-shaped signal dicts, each quoting its source sentence."""
    return analyze_note(raw_text, source)["signals"]


def raw_text_from_prompt(prompt: str) -> str:
    """Pull the research text out of EXTRACT_SIGNALS_PROMPT, ignoring its instructions."""
    marker = "Raw Research Text:"
    if marker not in prompt:
        return prompt
    body = prompt.split(marker, 1)[1]
    return body.split("\nSource:", 1)[0].strip()
