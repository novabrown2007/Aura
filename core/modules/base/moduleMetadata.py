"""Metadata model shared by all Aura modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModuleMetadata:
    """Public metadata advertised by an Aura module."""

    name: str
    version: str = "0.1.0"
    author: str = ""
    description: str = ""
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def fromDict(cls, values: dict[str, Any]):
        """Create metadata from a dictionary."""

        return cls(
            name=str(values["name"]),
            version=str(values.get("version", "0.1.0")),
            author=str(values.get("author", "")),
            description=str(values.get("description", "")),
            dependencies=tuple(values.get("dependencies", ())),
            permissions=tuple(values.get("permissions", ())),
            capabilities=tuple(values.get("capabilities", ())),
        )

    def asDict(self) -> dict[str, Any]:
        """Return metadata as a plain dictionary."""

        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "permissions": list(self.permissions),
            "capabilities": list(self.capabilities),
        }
