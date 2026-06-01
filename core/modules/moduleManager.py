"""Central module coordinator for Aura capability integrations."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Any

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata
from core.modules.base.moduleSubscription import ModuleSubscription
from core.modules.discovery import ModuleDescriptor, ModuleDiscovery
from core.modules.events.moduleEvents import ModuleEvents
from core.modules.lifecycle import ModuleLifecycleManager, ModuleState
from core.modules.moduleContext import ModuleContext
from core.modules.modulePermissions import ModulePermissions
from core.modules.moduleRegistry import ModuleRegistry
from core.modules.validation import ModuleValidator


class LegacyRegisteredModule(AuraModule):
    """Adapter for packages that still expose only `register(context)`."""

    def __init__(self, metadata: ModuleMetadata, package: ModuleType):
        super().__init__()
        self.metadata = metadata
        self.package = package

    def initialize(self, context):
        super().initialize(context)
        self.package.register(context)
        context.registerModule(self.metadata.name, self)


class ModuleManager:
    """Discover, load, and manage Aura modules."""

    RESERVED_PACKAGES = {"base", "database", "llm"}

    def __init__(self, context, packageName: str = "modules", package_name: str | None = None):
        self.context = context
        self.packageName = str(package_name or packageName or "modules")
        self.logger = context.logger.getChild("ModuleManager") if getattr(context, "logger", None) else None
        self.discovery = ModuleDiscovery(context, packageName=self.packageName)
        self.registry = ModuleRegistry(context)
        self.lifecycle = ModuleLifecycleManager(context, self.registry)
        self.validator = ModuleValidator(context)
        self.descriptors: dict[str, ModuleDescriptor] = {}
        self.loadedModules: dict[str, AuraModule] = {}
        self.disabledModules: set[str] = set()
        self.context.modules = getattr(self.context, "modules", {}) or {}
        self.context.moduleManager = self
        self.context.moduleLoader = self
        self.context.moduleRegistry = self.registry
        self.context.moduleDiscovery = self.discovery

        if self.logger:
            self.logger.info("Module manager initialized.")

    def loadModules(self):
        """Discover and load enabled modules in dependency order."""

        self.descriptors = self.discovery.discoverModules()
        for name in self._resolveLoadOrder():
            descriptor = self.descriptors[name]
            if descriptor.enabled:
                try:
                    self.loadModule(name)
                except Exception as error:
                    if self.logger:
                        self.logger.error(f"Failed to load module '{name}': {error}")
        return dict(self.loadedModules)

    def discoverModules(self):
        """Return currently discoverable module descriptors."""

        self.descriptors = self.discovery.discoverModules()
        return dict(self.descriptors)

    def loadModule(self, name: str):
        """Load one enabled module and its dependencies."""

        if name in self.loadedModules:
            return self.loadedModules[name]
        if name not in self.descriptors:
            if not self.descriptors:
                self.descriptors = self.discovery.discoverModules()
            if name not in self.descriptors:
                raise KeyError(f"Unknown Aura module: {name}")

        descriptor = self.descriptors[name]
        if not descriptor.enabled:
            self.disabledModules.add(name)
            self.registry.setState(name, ModuleState.DISABLED)
            return None

        for dependency in descriptor.metadata.dependencies:
            if dependency in self.descriptors and not self.descriptors[dependency].enabled:
                raise RuntimeError(f"Required Aura module dependency is disabled: {dependency}")
            if dependency not in self.loadedModules:
                self.loadModule(dependency)

        package = importlib.import_module(descriptor.import_path)
        moduleInstance = self._createModule(package, descriptor.metadata)
        moduleContext = ModuleContext(self.context, descriptor.metadata)
        modulePermissions = self._resolveModulePermissions(moduleInstance, descriptor.metadata)
        self.validator.ensureValid(moduleInstance, descriptor.metadata)
        self.registry.registerModule(name, moduleInstance, descriptor.metadata, modulePermissions)
        self.registry.registerIntents(name, self._normalizeDescriptors(moduleInstance.getIntents() if hasattr(moduleInstance, "getIntents") else []))
        self.registry.registerActions(name, self._normalizeDescriptors(moduleInstance.getActions() if hasattr(moduleInstance, "getActions") else []))
        self.registry.registerSubscriptions(name, self._normalizeSubscriptions(moduleInstance.getSubscriptions() if hasattr(moduleInstance, "getSubscriptions") else []))

        moduleInstance = self.lifecycle.loadModule(name, moduleInstance, moduleContext)
        self.loadedModules[name] = moduleInstance
        self.registry.registerModule(name, moduleInstance, descriptor.metadata, modulePermissions)
        setattr(self.context, name, moduleInstance)
        self._registerContextModule(name, moduleInstance)
        self._registerModuleTools(moduleInstance)
        self._subscribeModuleEvents(moduleInstance)

        if self.logger:
            self.logger.info(f"Loaded module: {name}")
        return moduleInstance

    def unloadModule(self, name: str):
        """Shutdown and unregister one loaded module."""

        module = self.loadedModules.pop(name, None)
        if module is None:
            return False

        self._unsubscribeModuleEvents(module)
        self._unregisterModuleTools(module)
        self.lifecycle.shutdownModule(name, module)
        self.context.modules.pop(name, None)
        if hasattr(self.context, name):
            setattr(self.context, name, None)
        contextAttribute = getattr(module, "context_attribute", None)
        if contextAttribute:
            self.context.modules.pop(contextAttribute, None)
            if hasattr(self.context, contextAttribute):
                setattr(self.context, contextAttribute, None)
        self.registry.setState(name, ModuleState.UNLOADED)
        if self.logger:
            self.logger.info(f"Unloaded module: {name}")
        return True

    def pauseModule(self, name: str, module: AuraModule | None = None):
        """Pause one loaded module."""

        module = module or self.loadedModules.get(name)
        if module is None:
            return False
        self.lifecycle.pauseModule(name, module)
        return True

    def resumeModule(self, name: str, module: AuraModule | None = None):
        """Resume one paused module."""

        module = module or self.loadedModules.get(name)
        if module is None:
            return False
        self.lifecycle.resumeModule(name, module)
        return True

    def shutdownModules(self):
        """Shutdown all loaded modules in reverse load order."""

        for name in list(reversed(list(self.loadedModules))):
            self.unloadModule(name)

    def reloadModule(self, name: str):
        """Hot reload one module package and initialize a fresh instance."""

        if name not in self.descriptors:
            self.descriptors = self.discovery.discoverModules()
        if name not in self.descriptors:
            raise KeyError(f"Unknown Aura module: {name}")

        descriptor = self.descriptors[name]
        self.unloadModule(name)
        self._reloadPackageTree(descriptor.import_path)

        package = importlib.import_module(descriptor.import_path)
        descriptor.metadata = self.discovery._readMetadata(descriptor.package_name, package)
        descriptor.enabled = self.discovery._isEnabled(descriptor.metadata.name)
        return self.loadModule(descriptor.metadata.name)

    def enableModule(self, name: str):
        """Enable a module for this runtime and load it."""

        if name not in self.descriptors:
            self.descriptors = self.discovery.discoverModules()
        if name not in self.descriptors:
            raise KeyError(f"Unknown Aura module: {name}")
        self.descriptors[name].enabled = True
        self.disabledModules.discard(name)
        return self.loadModule(name)

    def disableModule(self, name: str):
        """Disable and unload a module for this runtime."""

        if name in self.descriptors:
            self.descriptors[name].enabled = False
        self.disabledModules.add(name)
        result = self.unloadModule(name)
        self.registry.setState(name, ModuleState.DISABLED)
        return result

    def getMetadata(self, name: str | None = None):
        """Return metadata for one module or all discovered modules."""

        if not self.descriptors:
            self.descriptors = self.discovery.discoverModules()
        if name is not None:
            return self.descriptors[name].metadata
        return {key: descriptor.metadata for key, descriptor in self.descriptors.items()}

    def listCapabilities(self):
        """Return capabilities advertised by loaded modules."""

        if self.registry.entries:
            return self.registry.listCapabilities()
        capabilities = {}
        for name, module in self.loadedModules.items():
            capabilities[name] = list(module.metadata.capabilities)
        return capabilities

    def listPermissions(self):
        """Return permissions requested by loaded modules."""

        if self.registry.entries:
            return self.registry.listPermissions()
        permissions = {}
        for name, module in self.loadedModules.items():
            permissions[name] = list(module.metadata.permissions)
        return permissions

    def listStates(self):
        """Return lifecycle states for registered modules."""

        return self.registry.listStates()

    def getModule(self, name: str):
        """Return the live module instance when loaded."""

        return self.loadedModules.get(name)

    def _resolveLoadOrder(self):
        """Return module names ordered by dependencies."""

        ordered = []
        visiting = set()
        visited = set()

        def visit(moduleName):
            if moduleName in visited:
                return
            if moduleName in visiting:
                raise RuntimeError(f"Circular Aura module dependency involving {moduleName}")
            if moduleName not in self.descriptors:
                raise KeyError(f"Missing Aura module dependency: {moduleName}")

            visiting.add(moduleName)
            for dependency in self.descriptors[moduleName].metadata.dependencies:
                visit(dependency)
            visiting.remove(moduleName)
            visited.add(moduleName)
            ordered.append(moduleName)

        for name in sorted(self.descriptors):
            visit(name)
        return ordered

    def _registerModuleTools(self, module):
        """Register tools exposed by a loaded module."""

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None or not hasattr(module, "getTools"):
            return
        registry.registerTools(module.getTools())

    def _unregisterModuleTools(self, module):
        """Unregister tools exposed by an unloaded module."""

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None or not hasattr(module, "getTools"):
            return
        for tool in module.getTools():
            registry.unregisterTool(tool.name)

    def _subscribeModuleEvents(self, module):
        """Subscribe a module to declared event listeners when possible."""

        subscriptions = getattr(module, "getSubscriptions", None)
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None or not callable(subscriptions):
            return

        for subscription in self._normalizeSubscriptions(subscriptions() or []):
            if not subscription.enabled:
                continue
            handler = self._resolveSubscriptionHandler(module, subscription)
            if handler is None:
                continue
            eventBus.subscribe(subscription.eventName, handler)

    def _unsubscribeModuleEvents(self, module):
        """Unsubscribe declared module event listeners when possible."""

        subscriptions = getattr(module, "getSubscriptions", None)
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None or not callable(subscriptions):
            return

        for subscription in self._normalizeSubscriptions(subscriptions() or []):
            handler = self._resolveSubscriptionHandler(module, subscription)
            if handler is None:
                continue
            eventBus.unsubscribe(subscription.eventName, handler)

    def _createModule(self, package: ModuleType, metadata: ModuleMetadata):
        """Create a module instance from a package."""

        if hasattr(package, "createModule"):
            module = package.createModule(self.context)
            if not isinstance(module, AuraModule):
                raise TypeError(f"{metadata.name}.createModule() must return an AuraModule.")
            return module
        if hasattr(package, "AuraModule"):
            module = package.AuraModule()
            if not isinstance(module, AuraModule):
                raise TypeError(f"{metadata.name}.AuraModule must inherit AuraModule.")
            return module
        if hasattr(package, "register"):
            return LegacyRegisteredModule(metadata, package)
        raise TypeError(f"{metadata.name} does not expose createModule(), AuraModule, or register().")

    def _registerContextModule(self, name: str, module):
        """Register a module against RuntimeContext or a lightweight context."""

        if hasattr(self.context, "registerModule"):
            self.context.registerModule(name, module)
            return
        if not hasattr(self.context, "modules") or getattr(self.context, "modules") is None:
            self.context.modules = {}
        self.context.modules[name] = module

    @staticmethod
    def _normalizeDescriptors(values):
        """Return a list of normalized intent/action descriptors."""

        return list(values or [])

    @staticmethod
    def _normalizeStrings(values):
        """Return a list of normalized string values."""

        return [str(value) for value in list(values or [])]

    @staticmethod
    def _normalizeSubscriptions(values):
        """Return a list of normalized subscription descriptors."""

        subscriptions = []
        for value in list(values or []):
            if isinstance(value, ModuleSubscription):
                subscriptions.append(value)
            else:
                subscriptions.append(ModuleSubscription(eventName=str(value)))
        return subscriptions

    @staticmethod
    def _resolveSubscriptionHandler(module, subscription: ModuleSubscription):
        """Return the callable handler bound to one subscription descriptor."""

        handlerName = str(subscription.handler or "").strip()
        if handlerName:
            handler = getattr(module, handlerName, None)
            if callable(handler):
                return handler
        handler = getattr(module, "handleEvent", None) or getattr(module, "onEvent", None)
        return handler if callable(handler) else None

    @staticmethod
    def _resolveModulePermissions(module, metadata: ModuleMetadata) -> ModulePermissions:
        """Normalize module permissions from either runtime state or metadata."""

        permissions = None
        if hasattr(module, "getPermissions") and callable(module.getPermissions):
            try:
                permissions = module.getPermissions()
            except Exception:
                permissions = None
        if not isinstance(permissions, ModulePermissions):
            permissions = getattr(module, "permissions", None)
        if isinstance(permissions, ModulePermissions) and permissions.asList():
            return permissions
        return ModulePermissions(capabilityPermissions=tuple(metadata.permissions or ()))

    @staticmethod
    def _reloadPackageTree(importPath: str):
        """Reload a package and already-imported children."""

        loadedNames = [
            name for name in sys.modules
            if name == importPath or name.startswith(f"{importPath}.")
        ]
        for moduleName in sorted(loadedNames, key=len, reverse=True):
            importlib.reload(sys.modules[moduleName])
