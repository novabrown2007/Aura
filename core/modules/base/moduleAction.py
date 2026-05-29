"""Standard action model for Aura modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModuleAction:
    """Describe one executable action exposed by a module."""

    name: str
    description: str = ""
    method: str = ""
    parameters: dict[str, object] = field(default_factory=dict)
    requiredParameters: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    safe: bool = True
    target: str = ""

    def asDict(self) -> dict[str, object]:
        """Return a serializable action description."""

        return {
            "name": str(self.name),
            "description": str(self.description or ""),
            "method": str(self.method or ""),
            "parameters": dict(self.parameters or {}),
            "requiredParameters": list(self.requiredParameters or ()),
            "permissions": list(self.permissions or ()),
            "capabilities": list(self.capabilities or ()),
            "safe": bool(self.safe),
            "target": str(self.target or ""),
        }
