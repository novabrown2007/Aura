"""Execution policy definition for Aura governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionPolicy:
    """Policy knobs for safety decisions."""

    name: str = "default"
    requireConfirmationForHighRisk: bool = True
    allowAutomationWithoutConfirmation: bool = False
    riskThresholdForConfirmation: str = "HIGH"
    denyCriticalAutomation: bool = True
    quietHoursEnabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "requireConfirmationForHighRisk": bool(self.requireConfirmationForHighRisk),
            "allowAutomationWithoutConfirmation": bool(self.allowAutomationWithoutConfirmation),
            "riskThresholdForConfirmation": self.riskThresholdForConfirmation,
            "denyCriticalAutomation": bool(self.denyCriticalAutomation),
            "quietHoursEnabled": bool(self.quietHoursEnabled),
            "metadata": dict(self.metadata or {}),
        }

