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
    requiredPermissions: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    website: str = ""

    def __post_init__(self):
        """Normalize the legacy and canonical permission fields."""

        required = tuple(self.requiredPermissions or ())
        legacy = tuple(self.permissions or ())
        if not required and legacy:
            object.__setattr__(self, "requiredPermissions", legacy)
        elif required and not legacy:
            object.__setattr__(self, "permissions", required)
        elif required != legacy:
            merged = tuple(dict.fromkeys((*required, *legacy)))
            object.__setattr__(self, "requiredPermissions", merged)
            object.__setattr__(self, "permissions", merged)

    @classmethod
    def fromDict(cls, values: dict[str, Any]):
        """Create metadata from a dictionary."""

        required_permissions = tuple(
            values.get("requiredPermissions", values.get("permissions", ()))
        )
        return cls(
            name=str(values["name"]),
            version=str(values.get("version", "0.1.0")),
            author=str(values.get("author", "")),
            description=str(values.get("description", "")),
            dependencies=tuple(values.get("dependencies", ())),
            requiredPermissions=required_permissions,
            permissions=tuple(values.get("permissions", required_permissions)),
            capabilities=tuple(values.get("capabilities", ())),
            website=str(values.get("website", "")),
        )

    def asDict(self) -> dict[str, Any]:
        """Return metadata as a plain dictionary."""

        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "requiredPermissions": list(self.requiredPermissions),
            "permissions": list(self.permissions),
            "capabilities": list(self.capabilities),
            "website": self.website,
        }
