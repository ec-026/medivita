"""Conservative, non-diagnostic urgency signals for safety messaging."""

from __future__ import annotations

URGENT_SIGNALS = (
    "chest pain",
    "difficulty breathing",
    "can't breathe",
    "cannot breathe",
    "severe bleeding",
    "unconscious",
    "one-sided weakness",
    "sudden confusion",
    "suicidal",
    "overdose",
)


def has_urgent_signal(text: str) -> bool:
    lowered = text.lower()
    return any(signal in lowered for signal in URGENT_SIGNALS)


URGENT_NOTICE = (
    "Some details you shared can be associated with situations that need prompt evaluation. "
    "If you think this may be a medical emergency, contact your local emergency service or seek urgent medical care."
)
