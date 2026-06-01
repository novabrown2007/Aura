"""Standard intent model for Aura modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModuleIntent:
    """Describe one intent exposed by a module."""

    name: str
    description: str = ""
    arguments: dict[str, object] = field(default_factory=dict)
    target: str = ""
    requiredArguments: tuple[str, ...] = ()
    validationRequirements: tuple[str, ...] = ()

    def asDict(self) -> dict[str, object]:
        """Return a serializable intent description."""

        return {
            "name": str(self.name),
            "description": str(self.description or ""),
            "arguments": dict(self.arguments or {}),
            "target": str(self.target or ""),
            "requiredArguments": list(self.requiredArguments or ()),
            "validationRequirements": list(self.validationRequirements or ()),
        }
