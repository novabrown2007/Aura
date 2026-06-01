"""Selectable clarification option payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ClarificationOption:
    """Represent one possible clarification response."""

    optionId: str = field(default_factory=lambda: uuid4().hex)
    label: str = ""
    value: Any = None
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "optionId": self.optionId,
            "label": self.label,
            "value": self.value,
            "description": self.description,
            "metadata": dict(self.metadata or {}),
        }
