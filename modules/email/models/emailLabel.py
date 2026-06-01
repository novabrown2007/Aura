"""Email label model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailLabel:
    """Represent a provider or Aura local label."""

    labelId: str = ""
    name: str = ""
    color: str = ""
    system: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "labelId": self.labelId,
            "name": self.name,
            "color": self.color,
            "system": bool(self.system),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            labelId=str(values.get("labelId") or values.get("id") or ""),
            name=str(values.get("name") or ""),
            color=str(values.get("color") or ""),
            system=bool(values.get("system", False)),
            metadata=dict(values.get("metadata") or {}),
        )
