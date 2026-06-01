"""Constraint checks for execution actions."""

from __future__ import annotations


class ExecutionConstraintValidator:
    """Validate contextual constraints before execution."""

    def __init__(self, context=None):
        self.context = context

    def validate(self, request, actionDefinition=None):
        actionName = str(getattr(request, "action", "") or "")
        moduleName = str(getattr(actionDefinition, "module", "") or "")
        if not actionName:
            return False, "Missing action name."
        if actionDefinition is None:
            return False, f"Unknown action: {actionName}"
        moduleManager = getattr(self.context, "moduleManager", None)
        if moduleManager is not None and moduleName and hasattr(moduleManager, "registry"):
            entry = getattr(moduleManager.registry, "entries", {}).get(moduleName)
            if entry is not None and str(getattr(entry, "state", "")).upper() in {"ERROR", "DISABLED", "UNLOADED"}:
                return False, f"Module unavailable: {moduleName}"
        return True, None
