"""Email tag model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailTag:
    """Represent one Aura-local email tag."""

    tagId: str = ""
    name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "tagId": self.tagId,
            "name": self.name,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            tagId=str(values.get("tagId") or values.get("id") or ""),
            name=str(values.get("name") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
