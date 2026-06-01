"""Decision model for Aura execution governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionDecision:
    """Result of centralized execution validation."""

    decision: str = "DENIED"
    reason: str = ""
    requiresConfirmation: bool = False
    riskLevel: str = "LOW"
    cooldownRemaining: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def canExecute(self) -> bool:
        return self.decision == "SAFE"

    def asDict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "requiresConfirmation": bool(self.requiresConfirmation),
            "riskLevel": self.riskLevel,
            "cooldownRemaining": float(self.cooldownRemaining or 0.0),
            "metadata": dict(self.metadata or {}),
        }

