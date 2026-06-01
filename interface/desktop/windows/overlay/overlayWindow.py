"""Overlay window helpers for Aura's Windows desktop shell."""

from __future__ import annotations

from typing import Any


class OverlayWindow:
    """Apply desktop-specific behavior to Aura's main Tk window."""

    def __init__(self, context=None, window=None):
        self.context = context
        self.window = window
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.OverlayWindow") if logger else None

    def bindWindow(self, window):
        self.window = window
        self.applyPreferences()

    def applyPreferences(self):
        window = self.window
        if window is None:
            return
        try:
            # The primary Windows shell should remain opaque and behave like a
            # normal app window. Overlay transparency is applied only to the
            # floating bubble surfaces, not to the main application window.
            return
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Overlay preferences failed: {error}")

    def show(self):
        window = self.window
        if window is None:
            return
        try:
            window.deiconify()
            window.lift()
            window.focus_force()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Overlay show failed: {error}")

    def hide(self):
        window = self.window
        if window is None:
            return
        try:
            window.withdraw()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Overlay hide failed: {error}")

    def toggleCompactMode(self, compact: bool):
        if self.window is None:
            return
        try:
            if compact:
                self.window.geometry("380x190")
            else:
                self.window.geometry("900x620")
        except Exception:
            pass

    def snapshot(self) -> dict[str, Any]:
        return {
            "alwaysOnTop": bool(self._getConfigValue("overlayAlwaysOnTop", True)),
            "opacity": float(self._getConfigValue("overlayOpacity", 0.92)),
            "compactMode": bool(self._getConfigValue("overlayCompactMode", True)),
        }

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, None)
        if value is None and "." not in key:
            value = config.get(f"interface.desktop.windows.{key}", None)
        if value is None:
            return default
        return value
