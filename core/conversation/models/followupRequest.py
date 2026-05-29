"""Follow-up request model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FollowupRequest:
    """Resolved view of a user turn before provider processing."""

    originalText: str
    resolvedText: str
    isFollowup: bool = False
    resolvedReferences: dict[str, str] = field(default_factory=dict)
    activeTopic: str = ""
    activeEntity: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "originalText": self.originalText,
            "resolvedText": self.resolvedText,
            "isFollowup": self.isFollowup,
            "resolvedReferences": dict(self.resolvedReferences),
            "activeTopic": self.activeTopic,
            "activeEntity": self.activeEntity,
            "metadata": dict(self.metadata),
        }

