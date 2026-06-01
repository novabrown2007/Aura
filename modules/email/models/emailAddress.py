"""Email address model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmailAddress:
    """Represent one email address and display name."""

    address: str = ""
    displayName: str = ""
    isDefault: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "displayName": self.displayName,
            "isDefault": bool(self.isDefault),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            address=str(values.get("address") or ""),
            displayName=str(values.get("displayName") or values.get("name") or ""),
            isDefault=bool(values.get("isDefault", False)),
            metadata=dict(values.get("metadata") or {}),
        )
