"""Intent test helpers for assistant ecosystem simulations."""

from __future__ import annotations

from typing import Any


class IntentTester:
    """Validate structured intent generation and bridge requests."""

    def __init__(self, context=None, tracer=None, intentDebugger=None):
        self.context = context
        self.tracer = tracer
        self.intentDebugger = intentDebugger
        self.logger = context.logger.getChild("Testing.IntentTester") if context and getattr(context, "logger", None) else None

    def normalizeArguments(self, arguments: dict[str, Any] | None):
        """Normalize intent arguments into deterministic types."""

        normalized = {}
        for key, value in dict(arguments or {}).items():
            if isinstance(value, str) and value.isdigit():
                normalized[key] = int(value)
            else:
                normalized[key] = value
        return normalized

    def validateIntent(self, intent: dict[str, Any]):
        """Validate a structured intent payload."""

        name = str(intent.get("intent") or "").strip()
        confidence = float(intent.get("confidence", 0.0))
        arguments = intent.get("arguments") if isinstance(intent.get("arguments"), dict) else {}

        if not name:
            message = "Intent name is required."
            if self.intentDebugger:
                self.intentDebugger.recordValidationFailure(name, message, arguments)
            return False, message
        if confidence < 0.0 or confidence > 1.0:
            message = "Intent confidence must be between 0 and 1."
            if self.intentDebugger:
                self.intentDebugger.recordValidationFailure(name, message, arguments)
            return False, message
        return True, ""

    def buildBridgeRequest(self, intent: dict[str, Any], sessionId: str = "", interface: str = "desktop"):
        """Build one assistant.intent bridge request payload."""

        normalized = {
            "intent": str(intent.get("intent") or ""),
            "confidence": float(intent.get("confidence", 0.0)),
            "arguments": self.normalizeArguments(intent.get("arguments") if isinstance(intent.get("arguments"), dict) else {}),
        }
        payload = {
            "category": "assistant.intent",
            "context": {
                "sessionId": sessionId,
                "interface": interface,
            },
            "data": normalized,
        }
        if self.tracer:
            self.tracer.traceIntent(normalized)
        return payload

    def rejectInvalidIntent(self, intent: dict[str, Any]):
        """Return a structured invalid-intent failure."""

        valid, message = self.validateIntent(intent)
        if valid:
            return None
        payload = {"success": False, "error": message, "intent": dict(intent or {})}
        if self.logger:
            self.logger.warning(message)
        return payload
