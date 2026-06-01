"""Validation helpers for Aura modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleAction import ModuleAction
from core.modules.base.moduleIntent import ModuleIntent
from core.modules.base.moduleMetadata import ModuleMetadata
from core.modules.base.moduleSubscription import ModuleSubscription
from core.modules.modulePermissions import ModulePermissions


@dataclass
class ModuleValidationReport:
    """Result of validating one module or module package."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ModuleValidator:
    """Validate module structure, metadata, and exposed contract objects."""

    REQUIRED_LIFECYCLE_METHODS = ("initialize", "startup", "shutdown", "pause", "resume", "reload")

    def __init__(self, context=None):
        self.context = context
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("ModuleValidator") if getattr(context, "logger", None) else None

    def validatePackage(self, package: Any) -> ModuleValidationReport:
        """Validate a module package before it is loaded."""

        report = ModuleValidationReport()
        if not any(hasattr(package, attribute) for attribute in ("createModule", "AuraModule", "register")):
            report.valid = False
            report.errors.append("Module package must expose createModule(), AuraModule, or register().")
        metadata = getattr(package, "MODULE_METADATA", None)
        if metadata is not None and not isinstance(metadata, (ModuleMetadata, dict)):
            report.valid = False
            report.errors.append("MODULE_METADATA must be a ModuleMetadata instance or dictionary.")
        return report

    def validateModule(self, module: Any, metadata: ModuleMetadata | None = None) -> ModuleValidationReport:
        """Validate an instantiated module."""

        report = ModuleValidationReport()
        if not isinstance(module, AuraModule) and not self._looksLikeAuraModule(module):
            report.valid = False
            report.errors.append("Module must inherit AuraModule.")

        metadata = metadata or getattr(module, "metadata", None)
        if not isinstance(metadata, ModuleMetadata):
            report.valid = False
            report.errors.append("Module metadata must be a ModuleMetadata instance.")
        else:
            self._validateMetadata(metadata, report)

        for methodName in self.REQUIRED_LIFECYCLE_METHODS:
            if not callable(getattr(module, methodName, None)):
                report.valid = False
                report.errors.append(f"Module must define lifecycle method: {methodName}")

        self._validateDescriptors("intents", getattr(module, "getIntents", None), (ModuleIntent, str), report)
        self._validateDescriptors("actions", getattr(module, "getActions", None), (ModuleAction, str), report)
        self._validateDescriptors("subscriptions", getattr(module, "getSubscriptions", None), (ModuleSubscription, str), report)

        permissions = getattr(module, "getPermissions", None)
        if callable(permissions):
            try:
                value = permissions()
                if not isinstance(value, ModulePermissions):
                    report.warnings.append("Module getPermissions() should return ModulePermissions.")
            except Exception as error:
                report.valid = False
                report.errors.append(f"Module permission check failed: {error}")

        return report

    def ensureValid(self, module: Any, metadata: ModuleMetadata | None = None) -> ModuleValidationReport:
        """Raise a ValueError when validation fails."""

        report = self.validateModule(module, metadata=metadata)
        if not report.valid:
            raise ValueError("; ".join(report.errors) or "Invalid Aura module.")
        return report

    def _validateMetadata(self, metadata: ModuleMetadata, report: ModuleValidationReport):
        """Validate metadata contents."""

        if not str(metadata.name or "").strip():
            report.valid = False
            report.errors.append("Module metadata must include a non-empty name.")
        if not isinstance(metadata.dependencies, tuple):
            report.valid = False
            report.errors.append("Module metadata dependencies must be a tuple.")
        if not isinstance(metadata.requiredPermissions, tuple):
            report.valid = False
            report.errors.append("Module metadata requiredPermissions must be a tuple.")
        if not isinstance(metadata.capabilities, tuple):
            report.valid = False
            report.errors.append("Module metadata capabilities must be a tuple.")

    @staticmethod
    def _validateDescriptors(label: str, getter, allowedTypes, report: ModuleValidationReport):
        """Validate a module's exposed descriptors."""

        if not callable(getter):
            return
        try:
            values = getter() or []
        except Exception as error:
            report.valid = False
            report.errors.append(f"Module {label} getter failed: {error}")
            return
        for item in values:
            if not isinstance(item, allowedTypes):
                report.valid = False
                report.errors.append(f"Module {label} must contain only supported descriptor types.")
                return

    @staticmethod
    def _looksLikeAuraModule(module: Any) -> bool:
        """Return whether an object matches the legacy Aura module surface."""

        return all(callable(getattr(module, method, None)) for method in ("initialize", "shutdown"))
