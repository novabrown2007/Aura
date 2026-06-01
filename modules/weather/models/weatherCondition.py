"""Weather condition model for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WeatherCondition:
    """Normalized weather condition description."""

    name: str = ""
    code: str = ""
    severity: str = ""
    icon: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "code": self.code,
            "severity": self.severity,
            "icon": self.icon,
            "description": self.description,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            name=str(values.get("name", "")),
            code=str(values.get("code", "")),
            severity=str(values.get("severity", "")),
            icon=str(values.get("icon", "")),
            description=str(values.get("description", "")),
            metadata=dict(values.get("metadata") or {}),
        )
