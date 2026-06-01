"""Metadata attached to structured assistant responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResponseMetadata:
    """Track response provenance and orchestration hints."""

    provider: str = ""
    generationTime: float | None = None
    confidence: float = 0.0
    modulesInvolved: list[str] = field(default_factory=list)
    intentsResolved: list[str] = field(default_factory=list)
    memoryReferences: list[str] = field(default_factory=list)
    interruptionFlags: dict[str, Any] = field(default_factory=dict)
    streamingEnabled: bool = False
    deliveryResults: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "generationTime": self.generationTime,
            "confidence": float(self.confidence or 0.0),
            "modulesInvolved": list(self.modulesInvolved or []),
            "intentsResolved": list(self.intentsResolved or []),
            "memoryReferences": list(self.memoryReferences or []),
            "interruptionFlags": dict(self.interruptionFlags or {}),
            "streamingEnabled": bool(self.streamingEnabled),
            "deliveryResults": dict(self.deliveryResults or {}),
            "notes": dict(self.notes or {}),
        }
