"""Follow-up prompt payload attached to structured assistant responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResponseFollowup:
    """Describe one clarification or continuation prompt."""

    prompt: str = ""
    kind: str = "clarification"
    required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "kind": self.kind,
            "required": bool(self.required),
            "metadata": dict(self.metadata or {}),
        }
