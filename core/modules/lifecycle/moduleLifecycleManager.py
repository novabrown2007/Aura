"""Lifecycle coordinator for Aura modules."""

from __future__ import annotations

from typing import Any

from core.modules.events.moduleEvents import ModuleEvents
from core.modules.lifecycle.moduleState import ModuleState


class ModuleLifecycleManager:
    """Coordinate module lifecycle transitions safely."""

    def __init__(self, context, registry=None):
        """Create a lifecycle coordinator."""

        self.context = context
        self.registry = registry
        self.logger = context.logger.getChild("ModuleLifecycle") if getattr(context, "logger", None) else None

    def loadModule(self, moduleName: str, module: Any, moduleContext):
        """Initialize and start one module with guarded lifecycle transitions."""

        self._setState(moduleName, ModuleState.LOADED)
        self._emit(ModuleEvents.LOADED, {"module": moduleName, "state": ModuleState.LOADED.value})
        try:
            module.initialize(moduleContext.runtime)
            self._setState(moduleName, ModuleState.INITIALIZED)
            self._emit(ModuleEvents.REGISTERED, {"module": moduleName, "state": ModuleState.INITIALIZED.value})

            if hasattr(module, "startup"):
                module.startup()
            self._setState(moduleName, ModuleState.RUNNING)
            self._emit(ModuleEvents.STARTED, {"module": moduleName, "state": ModuleState.RUNNING.value})
        except Exception as error:
            self._setState(moduleName, ModuleState.ERROR)
            self._emit(ModuleEvents.FAILED, {"module": moduleName, "error": str(error)})
            raise
        return module

    def pauseModule(self, moduleName: str, module: Any):
        """Pause a loaded module."""

        try:
            if hasattr(module, "pause"):
                module.pause()
            self._setState(moduleName, ModuleState.PAUSED)
            self._emit(ModuleEvents.PAUSED, {"module": moduleName})
        except Exception as error:
            self._setState(moduleName, ModuleState.ERROR)
            self._emit(ModuleEvents.FAILED, {"module": moduleName, "error": str(error)})
            raise

    def resumeModule(self, moduleName: str, module: Any):
        """Resume a paused module."""

        try:
            if hasattr(module, "resume"):
                module.resume()
            self._setState(moduleName, ModuleState.RUNNING)
            self._emit(ModuleEvents.RESUMED, {"module": moduleName})
        except Exception as error:
            self._setState(moduleName, ModuleState.ERROR)
            self._emit(ModuleEvents.FAILED, {"module": moduleName, "error": str(error)})
            raise

    def shutdownModule(self, moduleName: str, module: Any):
        """Shutdown one module safely."""

        try:
            if hasattr(module, "shutdown"):
                module.shutdown()
            self._setState(moduleName, ModuleState.UNLOADED)
            self._emit(ModuleEvents.STOPPED, {"module": moduleName})
            self._emit(ModuleEvents.UNLOADED, {"module": moduleName})
        except Exception as error:
            self._setState(moduleName, ModuleState.ERROR)
            self._emit(ModuleEvents.FAILED, {"module": moduleName, "error": str(error)})
            raise

    def _setState(self, moduleName: str, state: ModuleState):
        if self.registry is not None:
            self.registry.setState(moduleName, state)

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload)
