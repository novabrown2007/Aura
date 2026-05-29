"""Compatibility base module contract for legacy Aura imports."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata


class ServiceModule(AuraModule):
    """Adapter that exposes an existing Aura service through the module contract."""

    def __init__(
        self,
        metadata: ModuleMetadata,
        service_factory: Callable[[Any], Any],
        context_attribute: str | None = None,
        intents: Iterable[str] = (),
    ):
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
        if self.logger:
            self.logger.info(f"{self.metadata.name} service started as {self.context_attribute}.")

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
