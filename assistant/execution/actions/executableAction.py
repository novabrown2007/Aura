"""Executable action descriptor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class ExecutableAction:
    """Base description of an executable Aura action."""

    actionId: str = field(default_factory=lambda: uuid4().hex)
    actionName: str = ""
    module: str = ""
    category: str = "UTILITY"
    parameters: dict[str, Any] = field(default_factory=dict)
    requiredPermissions: tuple[str, ...] = field(default_factory=tuple)
    riskLevel: str = "LOW"
    isAsync: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "actionId": self.actionId,
            "actionName": self.actionName,
            "module": self.module,
            "category": self.category,
            "parameters": dict(self.parameters or {}),
            "requiredPermissions": list(self.requiredPermissions or ()),
            "riskLevel": self.riskLevel,
            "isAsync": bool(self.isAsync),
            "metadata": dict(self.metadata or {}),
        }

