"""Execution metadata payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionMetadata:
    """Additional execution details for observability and response generation."""

    modulesInvolved: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    automation: bool = False
    confirmed: bool = False
    deliveryResults: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "modulesInvolved": list(self.modulesInvolved or []),
            "permissions": list(self.permissions or []),
            "confidence": float(self.confidence or 0.0),
            "automation": bool(self.automation),
            "confirmed": bool(self.confirmed),
            "deliveryResults": dict(self.deliveryResults or {}),
            "notes": dict(self.notes or {}),
        }
