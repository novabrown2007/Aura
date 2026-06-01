"""Compatibility exports for legacy Aura module imports."""

from core.modules.base.moduleSubscription import ModuleSubscription
from modules.base.baseModule import AuraModule, ModuleMetadata, ServiceModule

__all__ = ["AuraModule", "ModuleMetadata", "ModuleSubscription", "ServiceModule"]
