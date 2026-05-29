"""Action tracking for conversational continuity."""

from __future__ import annotations

from time import time
from typing import Any


class ActionTracker:
    """Normalize executed actions into short-term context entries."""

    def fromIntent(self, intent: str, arguments: dict[str, Any], result: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "intent": str(intent or ""),
            "arguments": dict(arguments or {}),
            "result": dict(result or {}),
            "timestamp": time(),
        }

    @staticmethod
    def describe(action: dict[str, Any]) -> str:
        intent = str(action.get("intent") or "")
        arguments = action.get("arguments") or {}
        return f"{intent} {arguments}".strip()

