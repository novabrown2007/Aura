"""Central registry for Aura module metadata, actions, intents, and state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.modules.base.moduleAction import ModuleAction
from core.modules.base.moduleIntent import ModuleIntent
from core.modules.base.moduleMetadata import ModuleMetadata
from core.modules.lifecycle.moduleState import ModuleState
from core.modules.modulePermissions import ModulePermissions


@dataclass
class ModuleRegistryEntry:
    """One registered module and its associated metadata."""

    name: str
    module: Any
    metadata: ModuleMetadata
    permissions: ModulePermissions = field(default_factory=ModulePermissions)
    state: ModuleState = ModuleState.UNLOADED
    intents: list[ModuleIntent] = field(default_factory=list)
    actions: list[ModuleAction] = field(default_factory=list)
    subscriptions: list[str] = field(default_factory=list)


class ModuleRegistry:
    """Maintain the live set of Aura modules and their capabilities."""

    def __init__(self, context=None):
        self.context = context
        self.entries: dict[str, ModuleRegistryEntry] = {}

    def registerModule(
        self,
        name: str,
        module: Any,
        metadata: ModuleMetadata | None = None,
        permissions: ModulePermissions | None = None,
    ):
        """Register or update a module entry."""

        metadata = metadata or getattr(module, "metadata", ModuleMetadata(name=name))
        permissions = permissions or getattr(module, "permissions", ModulePermissions())
        entry = self.entries.get(name)
        if entry is None:
            entry = ModuleRegistryEntry(
                name=name,
                module=module,
                metadata=metadata,
                permissions=permissions,
            )
            self.entries[name] = entry
        else:
            entry.module = module
            entry.metadata = metadata
            entry.permissions = permissions
        return entry

    def registerIntents(self, name: str, intents: list[ModuleIntent | str]):
        """Store intent descriptors for a module."""

        entry = self.entries.setdefault(
            name,
            ModuleRegistryEntry(
                name=name,
                module=None,
                metadata=ModuleMetadata(name=name),
            ),
        )
        entry.intents = [intent if isinstance(intent, ModuleIntent) else ModuleIntent(name=str(intent)) for intent in intents]
        return entry.intents

    def registerActions(self, name: str, actions: list[ModuleAction | str]):
        """Store action descriptors for a module."""

        entry = self.entries.setdefault(
            name,
            ModuleRegistryEntry(
                name=name,
                module=None,
                metadata=ModuleMetadata(name=name),
            ),
        )
        entry.actions = [action if isinstance(action, ModuleAction) else ModuleAction(name=str(action)) for action in actions]
        return entry.actions

    def registerSubscriptions(self, name: str, subscriptions: list[str]):
        """Store event subscriptions requested by a module."""

        entry = self.entries.setdefault(
            name,
            ModuleRegistryEntry(
                name=name,
                module=None,
                metadata=ModuleMetadata(name=name),
            ),
        )
        entry.subscriptions = [str(subscription) for subscription in subscriptions]
        return entry.subscriptions

    def setState(self, name: str, state: ModuleState | str):
        """Update the lifecycle state of a registered module."""

        entry = self.entries.setdefault(
            name,
            ModuleRegistryEntry(
                name=name,
                module=None,
                metadata=ModuleMetadata(name=name),
            ),
        )
        entry.state = ModuleState(state)
        return entry.state

    def unregisterModule(self, name: str):
        """Remove a module from the registry."""

        return self.entries.pop(name, None)

    def getModule(self, name: str):
        """Return the live module instance."""

        entry = self.entries.get(name)
        return entry.module if entry is not None else None

    def getMetadata(self, name: str):
        """Return registered metadata for one module."""

        entry = self.entries[name]
        return entry.metadata

    def listMetadata(self):
        """Return metadata for all registered modules."""

        return {name: entry.metadata for name, entry in sorted(self.entries.items())}

    def listCapabilities(self):
        """Return all registered capability names by module."""

        return {
            name: list(entry.metadata.capabilities)
            for name, entry in sorted(self.entries.items())
        }

    def listPermissions(self):
        """Return requested permissions by module."""

        return {
            name: entry.permissions.asList()
            for name, entry in sorted(self.entries.items())
        }

    def listIntents(self):
        """Return registered intent descriptors by module."""

        return {
            name: [intent.asDict() for intent in entry.intents]
            for name, entry in sorted(self.entries.items())
        }

    def listActions(self):
        """Return registered action descriptors by module."""

        return {
            name: [action.asDict() for action in entry.actions]
            for name, entry in sorted(self.entries.items())
        }

    def listStates(self):
        """Return current module lifecycle states."""

        return {
            name: entry.state.value if isinstance(entry.state, ModuleState) else str(entry.state)
            for name, entry in sorted(self.entries.items())
        }

    def listModules(self):
        """Return live module instances keyed by module name."""

        return {
            name: entry.module
            for name, entry in sorted(self.entries.items())
            if entry.module is not None
        }

    def getModulesByCapability(self, capabilityName: str) -> list[Any]:
        """Return module instances advertising a capability."""

        return [
            entry.module
            for entry in self.entries.values()
            if entry.module is not None and capabilityName in entry.metadata.capabilities
        ]
