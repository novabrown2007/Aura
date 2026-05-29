"""Standard capability model for Aura modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleCapability:
    """Describe one standardized capability exposed by a module."""

    name: str
    description: str = ""

    def asDict(self) -> dict[str, str]:
        """Return a serializable capability description."""

        return {
            "name": str(self.name),
            "description": str(self.description or ""),
        }
