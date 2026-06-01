"""Manage stacked desktop notifications for Aura."""

from __future__ import annotations

from typing import Any


class NotificationStack:
    """Maintain a bounded list of active popup notifications."""

    def __init__(self, context=None):
        self.context = context
        self.popups = []
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.Notifications.Stack") if logger else None

    def add(self, popup):
        self.popups.append(popup)
        self._trim()
        self.reflow()

    def remove(self, popup):
        self.popups = [item for item in self.popups if item is not popup]
        self.reflow()

    def reflow(self):
        root = getattr(self.context, "_desktopOverlayRoot", None)
        if root is None:
            return
        try:
            screenWidth = int(root.winfo_screenwidth())
            screenHeight = int(root.winfo_screenheight())
            x = max(0, screenWidth - 340)
            y = max(0, screenHeight - 120)
            for index, popup in enumerate(reversed(self.popups)):
                window = getattr(popup, "window", None)
                if window is None:
                    continue
                offsetY = max(0, y - (index * 92))
                window.geometry(f"300x84+{x}+{offsetY}")
        except Exception as error:
            if self.logger:
                self.logger.debug(f"Notification stack reflow failed: {error}")

    def snapshot(self) -> dict[str, Any]:
        return {"active": len(self.popups)}

    def _trim(self):
        maxCount = int(self._getConfigValue("maxQueuedNotifications", 50))
        while len(self.popups) > maxCount:
            popup = self.popups.pop(0)
            try:
                popup.dismiss()
            except Exception:
                pass

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

