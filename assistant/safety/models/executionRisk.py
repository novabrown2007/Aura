"""Risk labels for Aura execution governance."""

from __future__ import annotations


class ExecutionRisk:
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def normalize(cls, value) -> str:
        text = str(value or "").strip().upper()
        return text if text in {cls.LOW, cls.MODERATE, cls.HIGH, cls.CRITICAL} else cls.LOW

