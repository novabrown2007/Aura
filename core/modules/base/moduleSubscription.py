"""Standard event subscription model for Aura modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModuleSubscription:
    """Describe one event subscription exposed by a module."""

    eventName: str
    handler: str = ""
    description: str = ""
    target: str = ""
    enabled: bool = True
    filter: dict[str, object] = field(default_factory=dict)

    def asDict(self) -> dict[str, object]:
        """Return a serializable subscription description."""

        return {
            "eventName": str(self.eventName),
            "handler": str(self.handler or ""),
            "description": str(self.description or ""),
            "target": str(self.target or ""),
            "enabled": bool(self.enabled),
            "filter": dict(self.filter or {}),
        }
