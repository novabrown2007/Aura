"""Module permission model for Aura capability integrations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModulePermissions:
    """Describe permissions requested by a module."""

    capabilityPermissions: tuple[str, ...] = field(default_factory=tuple)
    externalApiPermissions: tuple[str, ...] = field(default_factory=tuple)
    deviceAccessPermissions: tuple[str, ...] = field(default_factory=tuple)
    sensitiveActionPermissions: tuple[str, ...] = field(default_factory=tuple)

    def asList(self) -> list[str]:
        """Return all requested permissions as a deduplicated list."""

        merged = []
        for values in (
            self.capabilityPermissions,
            self.externalApiPermissions,
            self.deviceAccessPermissions,
            self.sensitiveActionPermissions,
        ):
            for value in values:
                if value not in merged:
                    merged.append(value)
        return merged
