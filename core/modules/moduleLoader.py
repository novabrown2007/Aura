"""Compatibility wrapper for Aura's canonical module manager."""

from __future__ import annotations

from core.modules.moduleManager import ModuleManager


class ModuleLoader(ModuleManager):
    """Legacy alias that preserves the old loader import path."""

    pass
