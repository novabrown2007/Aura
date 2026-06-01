"""Permission rule model for Aura governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PermissionRule:
    """Describe one permission requirement or restriction."""

    permission: str = ""
    required: bool = True
    module: str = ""
    action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "permission": self.permission,
            "required": bool(self.required),
            "module": self.module,
            "action": self.action,
            "metadata": dict(self.metadata or {}),
        }

