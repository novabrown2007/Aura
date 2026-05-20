"""Structured intent model used by Aura's deterministic execution pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StructuredIntent:
    """Validated LLM interpretation of a user request."""

    intent: str
    arguments: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    response: str = ""

    @classmethod
    def fromDict(cls, payload: dict[str, Any]):
        """Create an intent from parsed JSON."""

        return cls(
            intent=str(payload.get("intent") or "").strip(),
            arguments=payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {},
            confidence=float(payload.get("confidence") or 0.0),
            response=str(payload.get("response") or "").strip(),
        )

    def asDict(self) -> dict[str, Any]:
        """Return a clean serializable representation."""

        return {
            "intent": self.intent,
            "arguments": self.arguments,
            "confidence": self.confidence,
            "response": self.response,
        }
