"""Route actions to module methods."""

from __future__ import annotations

from typing import Any


class ModuleActionRouter:
    """Execute module-owned actions."""

    def __init__(self, context=None):
        self.context = context

    def route(self, request, actionDefinition, confirmed: bool = False, allowAdmin: bool = False):
        moduleName = str(getattr(actionDefinition, "module", "") or "")
        methodName = str(getattr(actionDefinition, "executionHandler", "") or getattr(actionDefinition, "metadata", {}).get("method", "") or "").strip()
        if not moduleName:
            raise RuntimeError("Missing module for action.")
        module = self._resolveModule(moduleName)
        if module is None:
            raise RuntimeError(f"Module unavailable: {moduleName}")
        if not methodName:
            methodName = actionDefinition.actionName.split(".", 1)[-1]
        if not hasattr(module, methodName):
            raise RuntimeError(f"Module method unavailable: {methodName}")
        method = getattr(module, methodName)
        return method(**dict(getattr(request, "parameters", {}) or {}))

    def _resolveModule(self, moduleName: str):
        if hasattr(self.context, moduleName):
            module = getattr(self.context, moduleName)
            if module is not None:
                return module
        modules = getattr(self.context, "modules", {}) or {}
        return modules.get(moduleName)
