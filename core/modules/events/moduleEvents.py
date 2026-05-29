"""Module framework event names."""

from __future__ import annotations


class ModuleEvents:
    """Canonical events emitted by the module framework."""

    LOADED = "module.loaded"
    STARTED = "module.started"
    STOPPED = "module.stopped"
    FAILED = "module.failed"
    REGISTERED = "module.registered"
    UNLOADED = "module.unloaded"
    PAUSED = "module.paused"
    RESUMED = "module.resumed"
