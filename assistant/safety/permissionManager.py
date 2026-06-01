"""Permission evaluation for Aura execution governance."""

from __future__ import annotations

from assistant.safety.models import PermissionRule


class PermissionManager:
    """Evaluate module and tool permissions before execution."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.Permission") if logger else None

    def evaluate(self, request, tool=None):
        """Return whether the module/tool permissions are satisfied."""

        requiredPermissions = set(getattr(tool, "requiredPermissions", ()) or ())
        metadataPermissions = set()
        moduleName = str(getattr(request, "module", "") or "")
        actionName = str(getattr(request, "action", "") or "")

        moduleManager = getattr(self.context, "moduleManager", None)
        if moduleManager is not None and hasattr(moduleManager, "registry") and moduleName in getattr(moduleManager.registry, "entries", {}):
            entry = moduleManager.registry.entries[moduleName]
            metadataPermissions.update(getattr(entry.metadata, "permissions", ()) or ())
            metadataPermissions.update(getattr(entry.metadata, "requiredPermissions", ()) or ())

        missing = sorted(permission for permission in requiredPermissions if permission not in metadataPermissions and permission not in self._grantedPermissions())
        if missing:
            return False, missing, PermissionRule(permission=",".join(missing), module=moduleName, action=actionName, metadata={"reason": "missing_permission"})
        return True, [], None

    def _grantedPermissions(self) -> set[str]:
        config = getattr(self.context, "config", None)
        granted = set()
        if config is None or not hasattr(config, "get"):
            return granted
        values = config.get("safety.grantedPermissions", [])
        if isinstance(values, (list, tuple, set)):
            granted.update(str(value) for value in values)
        return granted

