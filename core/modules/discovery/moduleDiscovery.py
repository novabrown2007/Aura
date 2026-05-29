"""Automatic discovery of Aura capability modules."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata


@dataclass
class ModuleDescriptor:
    """Discovered module package and resolved metadata."""

    package_name: str
    import_path: str
    metadata: ModuleMetadata
    enabled: bool


class ModuleDiscovery:
    """Scan the `modules` package for loadable Aura modules."""

    RESERVED_PACKAGES = {"base", "database", "llm"}

    def __init__(self, context, packageName: str = "modules"):
        """Create a discovery helper for the module package tree."""

        self.context = context
        self.packageName = packageName
        self.logger = context.logger.getChild("ModuleDiscovery") if getattr(context, "logger", None) else None

    def discoverModules(self) -> dict[str, ModuleDescriptor]:
        """Discover importable module packages and read their metadata."""

        rootPackage = importlib.import_module(self.packageName)
        descriptors: dict[str, ModuleDescriptor] = {}
        for moduleInfo in pkgutil.iter_modules(rootPackage.__path__):
            if moduleInfo.name in self.RESERVED_PACKAGES:
                continue
            importPath = f"{self.packageName}.{moduleInfo.name}"
            package = importlib.import_module(importPath)
            if not self._isLoadablePackage(package):
                continue
            metadata = self._readMetadata(moduleInfo.name, package)
            enabled = self._isEnabled(metadata.name)
            descriptors[metadata.name] = ModuleDescriptor(
                package_name=moduleInfo.name,
                import_path=importPath,
                metadata=metadata,
                enabled=enabled,
            )
        return descriptors

    def _readMetadata(self, fallbackName: str, package: ModuleType):
        """Read module metadata from a package."""

        rawMetadata = getattr(package, "MODULE_METADATA", None)
        if isinstance(rawMetadata, ModuleMetadata):
            return rawMetadata
        if isinstance(rawMetadata, dict):
            return ModuleMetadata.fromDict(rawMetadata)
        if hasattr(package, "getMetadata"):
            metadata = package.getMetadata()
            if isinstance(metadata, ModuleMetadata):
                return metadata
            if isinstance(metadata, dict):
                return ModuleMetadata.fromDict(metadata)
        return ModuleMetadata(name=fallbackName)

    def _isEnabled(self, moduleName: str):
        """Return whether a module is enabled by config."""

        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return True

        for alias in self._moduleConfigAliases(moduleName):
            moduleConfig = config.get(f"modules.{alias}", None)
            parsed = self._parseModuleStatus(moduleConfig)
            if parsed is not None:
                return parsed

        enabledModules = config.get("modules.enabled", None)
        if isinstance(enabledModules, list):
            enabledAliases = {self._normalizeModuleName(name) for name in enabledModules}
            return self._normalizeModuleName(moduleName) in enabledAliases

        disabledModules = config.get("modules.disabled", [])
        disabledAliases = (
            {self._normalizeModuleName(name) for name in disabledModules}
            if isinstance(disabledModules, list)
            else set()
        )
        if self._normalizeModuleName(moduleName) in disabledAliases:
            return False

        return True

    @staticmethod
    def _parseModuleStatus(value):
        """Parse user-facing module status values."""

        if isinstance(value, dict) and "enabled" in value:
            return ModuleDiscovery._parseModuleStatus(value["enabled"])
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"enabled", "enable", "on", "true", "yes", "1"}:
                return True
            if normalized in {"disabled", "disable", "off", "false", "no", "0"}:
                return False
        return None

    @classmethod
    def _moduleConfigAliases(cls, moduleName: str) -> list[str]:
        """Return config key aliases for a module metadata name."""

        aliases = [str(moduleName)]
        snake = cls._camelToSnake(moduleName)
        normalized = cls._normalizeModuleName(moduleName)
        for alias in (snake, normalized):
            if alias and alias not in aliases:
                aliases.append(alias)
        return aliases

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
    def _isLoadablePackage(package: ModuleType):
        """Return whether a package exposes a module load hook."""

        return any(
            hasattr(package, attribute)
            for attribute in ("createModule", "AuraModule", "register")
        )
