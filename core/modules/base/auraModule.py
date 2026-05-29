"""Base class for all Aura modules."""

from __future__ import annotations

from typing import Any, Iterable

from core.modules.base.moduleAction import ModuleAction
from core.modules.base.moduleIntent import ModuleIntent
from core.modules.base.moduleMetadata import ModuleMetadata
from core.modules.moduleContext import ModuleContext
from core.modules.modulePermissions import ModulePermissions


class AuraModule:
    """Base class for Aura capability modules.

    Modules may override lifecycle hooks, declare intents and actions, and
    subscribe to events through the module manager. The base class keeps the
    legacy `modules.base.AuraModule` contract intact while exposing the new
    module framework primitives.
    """

    metadata = ModuleMetadata(name="module")

    def __init__(self):
        """Initialize base module state."""

        self.context = None
        self.moduleContext: ModuleContext | None = None
        self.logger = None
        self.state = None
        self.permissions = ModulePermissions()

    def initialize(self, context):
        """Bind the module to a runtime context."""

        self.context = context
        self.moduleContext = ModuleContext(context, self.metadata)
        if getattr(self, "logger", None) is None and getattr(context, "logger", None):
            self.logger = context.logger.getChild(self.metadata.name)

    def startup(self):
        """Start the module after initialization."""

    def pause(self):
        """Pause module activity."""

    def resume(self):
        """Resume paused module activity."""

    def shutdown(self):
        """Release module resources."""

    def _logStartup(self, message: str | None = None):
        """Emit one startup log line when the module has a logger."""

        logger = getattr(self, "logger", None)
        if logger:
            logger.info(message or f"{self.metadata.name} module started.")

    def getMetadata(self) -> ModuleMetadata:
        """Return the module metadata."""

        return self.metadata

    def getCapabilities(self) -> list[str]:
        """Return standardized capability names."""

        return list(self.metadata.capabilities)

    def getIntents(self) -> list[str | ModuleIntent]:
        """Return intent names or descriptors handled by the module."""

        return []

    def getActions(self) -> list[str | ModuleAction]:
        """Return action descriptors exposed by the module."""

        return []

    def getSubscriptions(self) -> list[str]:
        """Return event names the module would like to subscribe to."""

        return []

    def getPermissions(self) -> ModulePermissions:
        """Return module permission requirements."""

        return self.permissions

    def getConfig(self, key: str, default: Any = None):
        """Read module-specific configuration through the shared runtime."""

        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    def emit(self, eventName: str, data: dict[str, Any] | None = None):
        """Emit an event through the shared runtime event bus."""

        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, data or {})

    def canHandle(self, intent):
        """Return whether this module can handle the supplied intent."""

        intent_name = getattr(intent, "name", intent)
        for handled in self.getIntents():
            handled_name = getattr(handled, "name", handled)
            if handled_name == intent_name:
                return True
        return False

    def handleIntent(self, intent):
        """Handle an intent routed to this module."""

        raise NotImplementedError(f"{self.metadata.name} does not handle intents.")

    def handle(self, intent):
        """Compatibility wrapper for existing intent routing APIs."""

        return self.handleIntent(intent)

    @staticmethod
    def _toList(values: Iterable[Any] | None) -> list[Any]:
        """Normalize iterable-like values to a list."""

        if values is None:
            return []
        return list(values)
