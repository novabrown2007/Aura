"""Small animation coordinator for Aura's Windows bubble."""

from __future__ import annotations

from typing import Any


class OverlayAnimator:
    """Manage low-cost attention animations for the overlay."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.OverlayAnimator") if logger else None
        self.enabled = bool(self._getConfigValue("overlayAnimationsEnabled", True))
        self.active = False
        self.phase = 0
        self.target = None

    def startPulse(self, target):
        self.target = target
        self.active = True
        self.phase = 0
        self._tick()

    def stopPulse(self):
        self.active = False
        self.target = None

    def _tick(self):
        if not self.active or self.target is None:
            return
        self.phase = (self.phase + 1) % 10
        if hasattr(self.target, "setAnimationPhase"):
            try:
                self.target.setAnimationPhase(self.phase)
            except Exception:
                pass
        after = getattr(self.target, "after", None)
        if callable(after) and self.enabled:
            try:
                after(120, self._tick)
            except Exception:
                self.stopPulse()

    def snapshot(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "active": self.active, "phase": self.phase}

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

