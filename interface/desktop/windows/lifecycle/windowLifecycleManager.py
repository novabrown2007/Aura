"""Window lifecycle behavior for Aura's Windows desktop shell."""

from __future__ import annotations

from typing import Any


class WindowLifecycleManager:
    """Control minimize-to-tray and restore behavior for the desktop shell."""

    def __init__(self, context=None, app=None, stateManager=None, positionManager=None):
        self.context = context
        self.app = app
        self.stateManager = stateManager
        self.positionManager = positionManager
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.Lifecycle") if logger else None
        self.minimizeToTrayOnClose = bool(self._getConfigValue("minimizeToTrayOnClose", True))
        self.overlayStartMinimized = bool(self._getConfigValue("overlayStartMinimized", False))
        self.closeBehavior = "tray" if self.minimizeToTrayOnClose else "exit"

    def bindWindow(self, window):
        self.window = window
        if self.overlayStartMinimized:
            self.minimizeWindow()

    def handleCloseRequest(self) -> bool:
        """Return True when the close event was consumed and the app should remain running."""

        if self.closeBehavior == "tray":
            self.minimizeWindow()
            return True
        self.requestExit()
        return False

    def minimizeWindow(self):
        window = getattr(self, "window", None)
        if window is not None:
            try:
                if self.positionManager is not None:
                    self.positionManager.captureWindowPosition(window)
                window.withdraw()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Window minimize failed: {error}")
        if self.stateManager is not None:
            self.stateManager.setVisible(False)
            self.stateManager.setMinimizedToTray(True)

    def restoreWindow(self):
        window = getattr(self, "window", None)
        if window is not None:
            try:
                window.deiconify()
                window.lift()
                window.focus_force()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Window restore failed: {error}")
            if self.positionManager is not None:
                self.positionManager.restoreWindowPosition(window)
        if self.stateManager is not None:
            self.stateManager.setVisible(True)
            self.stateManager.setMinimizedToTray(False)

    def requestExit(self):
        if self.stateManager is not None:
            self.stateManager.setVisible(False)
            self.stateManager.setMinimizedToTray(False)
        if self.app is not None and hasattr(self.app, "requestExit"):
            self.app.requestExit()
        elif getattr(self.context, "should_exit", None) is not None:
            self.context.should_exit = True
        window = getattr(self, "window", None)
        if window is not None:
            try:
                window.quit()
            except Exception:
                pass

    def snapshot(self) -> dict[str, Any]:
        return {
            "closeBehavior": self.closeBehavior,
            "minimizeToTrayOnClose": self.minimizeToTrayOnClose,
            "overlayStartMinimized": self.overlayStartMinimized,
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
