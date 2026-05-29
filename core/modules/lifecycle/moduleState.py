"""Module lifecycle state enumeration."""

from __future__ import annotations

from enum import Enum


class ModuleState(str, Enum):
    """Lifecycle states for Aura modules."""

    UNLOADED = "UNLOADED"
    LOADED = "LOADED"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    DISABLED = "DISABLED"
