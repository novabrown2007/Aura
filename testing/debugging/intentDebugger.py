"""Intent debugging helpers for assistant simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class IntentRecord:
    """One traced assistant intent."""

    intent: str
    confidence: float
    arguments: dict[str, Any] = field(default_factory=dict)
    validation: str = "pending"
    response: str = ""
    createdAt: str = field(default_factory=_utcNow)


class IntentDebugger:
    """Trace generated intents, validation failures, and execution responses."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Testing.Intent") if context and getattr(context, "logger", None) else None
        self.records: list[IntentRecord] = []
        self.failures: list[dict[str, Any]] = []

    def recordIntent(self, intent: str, confidence: float = 1.0, arguments: dict[str, Any] | None = None):
        """Record one generated intent."""

        record = IntentRecord(intent=str(intent or ""), confidence=float(confidence), arguments=dict(arguments or {}))
        self.records.append(record)
        if self.logger:
            self.logger.debug(f"Intent recorded: {record.intent} ({record.confidence:.2f})")
        return record

    def recordValidationFailure(self, intent: str, message: str, arguments: dict[str, Any] | None = None):
        """Record a validation failure."""

        payload = {"intent": str(intent or ""), "message": str(message or ""), "arguments": dict(arguments or {})}
        self.failures.append(payload)
        if self.records:
            self.records[-1].validation = "failed"
        if self.logger:
            self.logger.warning(f"Intent validation failed: {payload['intent']} -> {payload['message']}")
        return payload

    def recordExecutionResponse(self, intent: str, response: str):
        """Record a successful or failed execution response."""

        if self.records:
            self.records[-1].response = str(response or "")
            self.records[-1].validation = "passed"
        if self.logger:
            self.logger.debug(f"Intent response: {intent}")
        return {"intent": str(intent or ""), "response": str(response or "")}

    def snapshot(self) -> dict[str, Any]:
        """Return intent trace state."""

        return {
            "intents": [
                {
                    "intent": record.intent,
                    "confidence": record.confidence,
                    "arguments": dict(record.arguments),
                    "validation": record.validation,
                    "response": record.response,
                    "createdAt": record.createdAt,
                }
                for record in self.records
            ],
            "validationFailures": list(self.failures),
        }

    def getLatestIntent(self):
        """Return the most recently recorded intent."""

        if not self.records:
            return None
        record = self.records[-1]
        return {
            "intent": record.intent,
            "confidence": record.confidence,
            "arguments": dict(record.arguments),
            "validation": record.validation,
            "response": record.response,
            "createdAt": record.createdAt,
        }
