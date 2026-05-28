"""Dynamic Aura module discovery, loading, and hot reload."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from dataclasses import dataclass
from types import ModuleType

from modules.base import AuraModule, ModuleMetadata


@dataclass
class ModuleDescriptor:
    """Discovered module package and resolved metadata."""

    package_name: str
    import_path: str
    metadata: ModuleMetadata
    enabled: bool


class LegacyRegisteredModule(AuraModule):
    """Adapter for packages that still expose only `register(context)`."""

    def __init__(self, metadata: ModuleMetadata, package: ModuleType):
        """Create a legacy adapter."""

        super().__init__()
        self.metadata = metadata
        self.package = package

    def initialize(self, context):
        """Call the legacy package register hook."""

        super().initialize(context)
        self.package.register(context)
        context.registerModule(self.metadata.name, self)


class ModuleLoader:
    """Discover and manage Aura modules from the `modules` package."""

    RESERVED_PACKAGES = {"base", "database", "llm"}

    def __init__(self, context, package_name: str = "modules"):
        """Initialize the module loader."""

        self.context = context
        self.package_name = package_name
        self.logger = context.logger.getChild("ModuleLoader") if context.logger else None
        self.descriptors: dict[str, ModuleDescriptor] = {}
        self.loadedModules: dict[str, AuraModule] = {}
        self.disabledModules: set[str] = set()
        self.context.moduleLoader = self

        if self.logger:
            self.logger.info("Module loader initialized.")

    def loadModules(self):
        """Discover and load enabled modules in dependency order."""

        self.descriptors = self.discoverModules()
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
        """Discover importable module packages and read their metadata."""

        root_package = importlib.import_module(self.package_name)
        descriptors = {}
        for module_info in pkgutil.iter_modules(root_package.__path__):
            if module_info.name in self.RESERVED_PACKAGES:
                continue
            import_path = f"{self.package_name}.{module_info.name}"
            package = importlib.import_module(import_path)
            if not self._isLoadablePackage(package):
                continue
            metadata = self._readMetadata(module_info.name, package)
            enabled = self._isEnabled(metadata.name)
            descriptors[metadata.name] = ModuleDescriptor(
                package_name=module_info.name,
                import_path=import_path,
                metadata=metadata,
                enabled=enabled,
            )
        return descriptors

    def loadModule(self, name: str):
        """Load one enabled module and its dependencies."""

        if name in self.loadedModules:
            return self.loadedModules[name]
        if name not in self.descriptors:
            raise KeyError(f"Unknown Aura module: {name}")

        descriptor = self.descriptors[name]
        if not descriptor.enabled:
            self.disabledModules.add(name)
            return None

        for dependency in descriptor.metadata.dependencies:
            if dependency in self.descriptors and not self.descriptors[dependency].enabled:
                raise RuntimeError(f"Required Aura module dependency is disabled: {dependency}")
            if dependency not in self.loadedModules:
                self.loadModule(dependency)

        package = importlib.import_module(descriptor.import_path)
        module_instance = self._createModule(package, descriptor.metadata)
        module_instance.initialize(self.context)
        setattr(self.context, name, module_instance)
        self.loadedModules[name] = module_instance
        self._registerContextModule(name, module_instance)
        self._registerModuleTools(module_instance)

        if self.logger:
            self.logger.info(f"Loaded module: {name}")
        return module_instance

    def unloadModule(self, name: str):
        """Shutdown and unregister one loaded module."""

        module = self.loadedModules.pop(name, None)
        if module is None:
            return False

        self._unregisterModuleTools(module)
        module.shutdown()
        self.context.modules.pop(name, None)
        context_attribute = getattr(module, "context_attribute", None)
        if context_attribute:
            self.context.modules.pop(context_attribute, None)
            if hasattr(self.context, context_attribute):
                setattr(self.context, context_attribute, None)
        if self.logger:
            self.logger.info(f"Unloaded module: {name}")
        return True

    def shutdownModules(self):
        """Shutdown all loaded modules in reverse load order."""

        for name in list(reversed(list(self.loadedModules))):
            self.unloadModule(name)

    def reloadModule(self, name: str):
        """Hot reload one module package and initialize a fresh instance."""

        if name not in self.descriptors:
            self.descriptors = self.discoverModules()
        if name not in self.descriptors:
            raise KeyError(f"Unknown Aura module: {name}")

        descriptor = self.descriptors[name]
        self.unloadModule(name)
        self._reloadPackageTree(descriptor.import_path)

        package = importlib.import_module(descriptor.import_path)
        descriptor.metadata = self._readMetadata(descriptor.package_name, package)
        descriptor.enabled = self._isEnabled(descriptor.metadata.name)
        return self.loadModule(descriptor.metadata.name)

    def enableModule(self, name: str):
        """Enable a module for this runtime and load it."""

        if name not in self.descriptors:
            self.descriptors = self.discoverModules()
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
        return self.unloadModule(name)

    def getMetadata(self, name: str | None = None):
        """Return metadata for one module or all discovered modules."""

        if not self.descriptors:
            self.descriptors = self.discoverModules()
        if name is not None:
            return self.descriptors[name].metadata
        return {key: descriptor.metadata for key, descriptor in self.descriptors.items()}

    def listCapabilities(self):
        """Return capabilities advertised by loaded modules."""

        capabilities = {}
        for name, module in self.loadedModules.items():
            capabilities[name] = list(module.metadata.capabilities)
        return capabilities

    def listPermissions(self):
        """Return permissions requested by loaded modules."""

        permissions = {}
        for name, module in self.loadedModules.items():
            permissions[name] = list(module.metadata.permissions)
        return permissions

    def _resolveLoadOrder(self):
        """Return module names ordered by dependencies."""

        ordered = []
        visiting = set()
        visited = set()

        def visit(name):
            if name in visited:
                return
            if name in visiting:
                raise RuntimeError(f"Circular Aura module dependency involving {name}")
            if name not in self.descriptors:
                raise KeyError(f"Missing Aura module dependency: {name}")

            visiting.add(name)
            for dependency in self.descriptors[name].metadata.dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            ordered.append(name)

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

    def _readMetadata(self, fallback_name: str, package: ModuleType):
        """Read module metadata from a package."""

        raw_metadata = getattr(package, "MODULE_METADATA", None)
        if isinstance(raw_metadata, ModuleMetadata):
            return raw_metadata
        if isinstance(raw_metadata, dict):
            return ModuleMetadata.fromDict(raw_metadata)
        if hasattr(package, "getMetadata"):
            metadata = package.getMetadata()
            if isinstance(metadata, ModuleMetadata):
                return metadata
            if isinstance(metadata, dict):
                return ModuleMetadata.fromDict(metadata)
        return ModuleMetadata(name=fallback_name)

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
                raise TypeError(f"{metadata.name}.AuraModule must inherit modules.base.AuraModule.")
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
    def _isLoadablePackage(package: ModuleType):
        """Return whether a package exposes a module load hook."""

        return any(
            hasattr(package, attribute)
            for attribute in ("createModule", "AuraModule", "register")
        )

    def _isEnabled(self, module_name: str):
        """Return whether a module is enabled by config."""

        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return True

        for alias in self._moduleConfigAliases(module_name):
            module_config = config.get(f"modules.{alias}", None)
            parsed = self._parseModuleStatus(module_config)
            if parsed is not None:
                return parsed

        enabled_modules = config.get("modules.enabled", None)
        if isinstance(enabled_modules, list):
            enabled_aliases = {self._normalizeModuleName(name) for name in enabled_modules}
            return self._normalizeModuleName(module_name) in enabled_aliases

        disabled_modules = config.get("modules.disabled", [])
        disabled_aliases = {self._normalizeModuleName(name) for name in disabled_modules} if isinstance(disabled_modules, list) else set()
        if self._normalizeModuleName(module_name) in disabled_aliases:
            return False

        return True

    @classmethod
    def _moduleConfigAliases(cls, module_name: str) -> list[str]:
        """Return config key aliases for a module metadata name."""

        aliases = [str(module_name)]
        snake = cls._camelToSnake(module_name)
        normalized = cls._normalizeModuleName(module_name)
        for alias in (snake, normalized):
            if alias and alias not in aliases:
                aliases.append(alias)
        return aliases

    @staticmethod
    def _parseModuleStatus(value):
        """Parse user-facing module status values."""

        if isinstance(value, dict) and "enabled" in value:
            return ModuleLoader._parseModuleStatus(value["enabled"])
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"enabled", "enable", "on", "true", "yes", "1"}:
                return True
            if normalized in {"disabled", "disable", "off", "false", "no", "0"}:
                return False
        return None

    @staticmethod
    def _normalizeModuleName(value) -> str:
        return str(value or "").replace("_", "").replace("-", "").lower()

    @staticmethod
    def _camelToSnake(value: str) -> str:
        result = []
        for index, character in enumerate(str(value or "")):
            if character.isupper() and index > 0:
                result.append("_")
            result.append(character.lower())
        return "".join(result)

    @staticmethod
    def _reloadPackageTree(import_path: str):
        """Reload a package and already-imported children."""

        loaded_names = [
            name for name in sys.modules
            if name == import_path or name.startswith(f"{import_path}.")
        ]
        for module_name in sorted(loaded_names, key=len, reverse=True):
            importlib.reload(sys.modules[module_name])
