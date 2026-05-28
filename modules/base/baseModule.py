"""Standard module contract for Aura plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class ModuleMetadata:
    """Public metadata advertised by an Aura module."""

    name: str
    version: str = "0.1.0"
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
            description=str(values.get("description", "")),
            dependencies=tuple(values.get("dependencies", ())),
            permissions=tuple(values.get("permissions", ())),
            capabilities=tuple(values.get("capabilities", ())),
        )

    def asDict(self):
        """Return metadata as a plain dictionary."""

        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "permissions": list(self.permissions),
            "capabilities": list(self.capabilities),
        }


class AuraModule:
    """Base class for Aura plugin modules."""

    metadata = ModuleMetadata(name="module")

    def __init__(self):
        """Initialize base module state."""

        self.context = None

    def initialize(self, context):
        """Initialize the module with a runtime context."""

        self.context = context

    def _logStartup(self, message: str | None = None):
        """Emit one startup log line when the module has a logger."""

        logger = getattr(self, "logger", None)
        if logger:
            logger.info(message or f"{self.metadata.name} module started.")

    def shutdown(self):
        """Release module resources."""

    def getIntents(self):
        """Return intent names or descriptors handled by the module."""

        return []

    def handleIntent(self, intent):
        """Handle an intent routed to this module."""

        raise NotImplementedError(f"{self.metadata.name} does not handle intents.")

    def canHandle(self, intent):
        """Return whether this module can handle the supplied intent."""

        intent_name = getattr(intent, "name", intent)
        return intent_name in self.getIntents()

    def handle(self, intent):
        """Compatibility wrapper for the existing IntentRouter API."""

        return self.handleIntent(intent)


class ServiceModule(AuraModule):
    """Adapter that exposes an existing Aura service through the module contract."""

    def __init__(
        self,
        metadata: ModuleMetadata,
        service_factory: Callable[[Any], Any],
        context_attribute: str | None = None,
        intents: Iterable[str] = (),
    ):
        """Create a service adapter module."""

        super().__init__()
        self.metadata = metadata
        self.service_factory = service_factory
        self.context_attribute = context_attribute or metadata.name
        self.intents = tuple(intents)
        self.service = None

    def initialize(self, context):
        """Create and register the wrapped service."""

        super().initialize(context)
        if getattr(self, "logger", None) is None and getattr(context, "logger", None):
            self.logger = context.logger.getChild(self.metadata.name)
        self.service = self.service_factory(context)
        setattr(context, self.context_attribute, self.service)
        self._registerContextModule(context, self.metadata.name, self)
        if self.context_attribute != self.metadata.name:
            self._registerContextModule(context, self.context_attribute, self.service)
        self._logStartup(f"{self.metadata.name} service started as {self.context_attribute}.")

    def shutdown(self):
        """Shutdown the wrapped service if it exposes a shutdown method."""

        if hasattr(self.service, "shutdown"):
            self.service.shutdown()

    def getIntents(self):
        """Return intents advertised by this adapter."""

        return list(self.intents)

    def handleIntent(self, intent):
        """Delegate intent handling to the wrapped service."""

        if hasattr(self.service, "handleIntent"):
            return self.service.handleIntent(intent)
        if hasattr(self.service, "handle"):
            return self.service.handle(intent)
        raise NotImplementedError(f"{self.metadata.name} does not handle intents.")

    @staticmethod
    def _registerContextModule(context, name: str, module):
        """Register with either RuntimeContext or a lightweight test context."""

        if hasattr(context, "registerModule"):
            context.registerModule(name, module)
            return
        if not hasattr(context, "modules") or getattr(context, "modules") is None:
            context.modules = {}
        context.modules[name] = module

