"""Coordinator for Aura's Windows desktop presence layer."""

from __future__ import annotations

import os
from typing import Any

from interface.desktop.windows.handlers.overlayEventHandler import OverlayEventHandler
from interface.desktop.windows.interaction.quickInteractionWindow import QuickInteractionWindow
from interface.desktop.windows.lifecycle.shutdownManager import ShutdownManager
from interface.desktop.windows.lifecycle.windowLifecycleManager import WindowLifecycleManager
from interface.desktop.windows.notifications.desktopNotificationManager import DesktopNotificationManager
from interface.desktop.windows.overlay.assistantBubble import AssistantBubble
from interface.desktop.windows.overlay.overlayAnimator import OverlayAnimator
from interface.desktop.windows.overlay.overlayPositionManager import OverlayPositionManager
from interface.desktop.windows.overlay.overlayStateManager import OverlayStateManager
from interface.desktop.windows.overlay.overlayWindow import OverlayWindow
from interface.desktop.windows.tray.systemTrayManager import SystemTrayManager
from interface.desktop.windows.tray.trayActions import TrayActions
from interface.desktop.windows.tray.trayMenu import TrayMenu, TrayMenuItem


class OverlayManager:
    """Manage the Windows overlay, tray, bubble, and notification surfaces."""

    def __init__(self, context=None, root=None, app=None):
        self.context = context
        self.root = root
        self.app = app
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.Overlay") if logger else None
        self.stateManager = OverlayStateManager(context)
        self.bubblePositionManager = OverlayPositionManager(
            context,
            storagePath=self._bubblePositionStoragePath(),
        )
        self.positionManager = self.bubblePositionManager
        self.overlayWindow = OverlayWindow(context, root)
        self.animator = OverlayAnimator(context)
        self.trayActions = TrayActions(self)
        self.trayManager = SystemTrayManager(context, self)
        self.notificationManager = DesktopNotificationManager(context, root, self.stateManager)
        self.bubble = AssistantBubble(context, root, onOpen=self.showWindow, positionManager=self.bubblePositionManager)
        self.quickInteractionWindow = QuickInteractionWindow(context, root, self)
        self.windowLifecycleManager = WindowLifecycleManager(context, app=app, stateManager=self.stateManager, positionManager=None)
        self.shutdownManager = ShutdownManager(context, app=app, overlayManager=self)
        self.eventHandler = OverlayEventHandler(context, self)
        self.started = False
        self.enabled = bool(self._getConfigValue("desktopOverlayEnabled", True))
        self._quickSubmitCallback = None
        if context is not None:
            context.desktopOverlayManager = self
            context.systemTrayManager = self.trayManager
            context.desktopNotificationManager = self.notificationManager
            context.overlayStateManager = self.stateManager
            context.assistantBubble = self.bubble
            context.windowLifecycleManager = self.windowLifecycleManager
            context.shutdownManager = self.shutdownManager
            context._desktopOverlayRoot = root

    def start(self):
        self.started = True
        if self.root is not None:
            self.overlayWindow.bindWindow(self.root)
            self.windowLifecycleManager.bindWindow(self.root)
        self.stateManager.setEnabled(self.enabled)
        self.eventHandler.subscribe()
        self.notificationManager.start()
        self.trayManager.configureMenu(self._buildTrayMenu(), self._buildTrayActionMap())
        self.trayManager.start()
        self.stateManager.setTrayActive(bool(self.trayManager.enabled and os.name == "nt"))
        if self._getConfigValue("overlayStartMinimized", False):
            self.hideWindow(showBubble=bool(self._getConfigValue("assistantBubbleEnabled", True)))
        else:
            self.stateManager.setVisible(True)
            if self._getConfigValue("assistantBubbleEnabled", True):
                self.showBubble()
        return self

    def shutdownUi(self):
        self.eventHandler.unsubscribe()
        self.trayManager.stop()
        self.notificationManager.shutdown()
        self.hideBubble()
        self.hideQuickInteraction()
        self.stateManager.setTrayActive(False)
        self.started = False

    def showWindow(self):
        self.windowLifecycleManager.restoreWindow()
        self.overlayWindow.applyPreferences()
        self.stateManager.setVisible(True)
        if self._getConfigValue("assistantBubbleEnabled", True):
            self.hideBubble()

    def hideWindow(self, showBubble: bool = True):
        self.windowLifecycleManager.minimizeWindow()
        self.overlayWindow.hide()
        self.stateManager.setVisible(False)
        if showBubble and self._getConfigValue("assistantBubbleEnabled", True):
            self.showBubble()

    def handleWindowCloseRequest(self) -> bool:
        if self.windowLifecycleManager.handleCloseRequest():
            if self._getConfigValue("assistantBubbleEnabled", True):
                self.showBubble()
            return True
        self.requestExit(reason="window-close")
        return False

    def requestExit(self, reason: str = "user"):
        self.shutdownManager.requestShutdown(reason=reason)

    def showBubble(self):
        self.stateManager.setBubbleVisible(True)
        self.bubble.show()

    def hideBubble(self):
        self.stateManager.setBubbleVisible(False)
        self.bubble.hide()

    def showQuickInteraction(self):
        self.quickInteractionWindow.show()
        self.stateManager.setQuickInteractionVisible(True)

    def hideQuickInteraction(self):
        self.quickInteractionWindow.hide()
        self.stateManager.setQuickInteractionVisible(False)

    def submitQuickInteraction(self, text: str | None = None):
        if text is None and hasattr(self.quickInteractionWindow, "entry"):
            try:
                text = self.quickInteractionWindow.entry.get().strip()
            except Exception:
                text = ""
        if not text:
            return
        if callable(self._quickSubmitCallback):
            self._quickSubmitCallback(text)

    def setQuickSubmitCallback(self, callback):
        self._quickSubmitCallback = callback
        self.quickInteractionWindow.setSubmitCallback(callback)

    def updateAssistant(self, state: str, message: str = ""):
        self.stateManager.updateAssistant(state=state, message=message)
        self.bubble.setState(state, message, provider=self._activeProviderName(), connected=self._providerConnected())

    def updateMic(self, state: str, activity: bool = False, muted: bool = False, confidence: float = 0.0, silence: float = 0.0):
        self.stateManager.updateAssistant(listening=state == "LISTENING", processing=state == "PROCESSING", responding=state == "RESPONDING")
        self.bubble.setMicState(state, active=activity, muted=muted, confidence=confidence, silence=silence)

    def setProcessing(self, active: bool, message: str = "Processing"):
        self.bubble.setProcessing(active, message)

    def updateConnection(self, connected: bool, provider: str = ""):
        self.stateManager.updateAssistant(connected=bool(connected), provider=provider)
        self.bubble.connectionIndicator.setState(connected, provider)

    def markEvent(self, eventName: str):
        self.stateManager.markEvent(eventName)

    def showNotification(self, notification: Any):
        self.notificationManager.showNotification(notification)

    def snapshot(self) -> dict[str, Any]:
        return {
            "available": True,
            "enabled": self.enabled,
            "state": self.stateManager.snapshot(),
            "tray": self.trayManager.snapshot(),
            "bubble": self.bubble.snapshot(),
            "notifications": self.notificationManager.snapshot(),
            "lifecycle": self.windowLifecycleManager.snapshot(),
            "position": self.positionManager.snapshot(),
            "shutdown": self.shutdownManager.snapshot(),
        }

    def _buildTrayMenu(self) -> TrayMenu:
        return TrayMenu(
            items=[
                TrayMenuItem(1001, "Open Aura", "openAura"),
                TrayMenuItem(1002, "Quick Conversation", "quickConversation"),
                TrayMenuItem(1003, "Mute Microphone", "muteMicrophone"),
                TrayMenuItem(1004, "Pause Listening", "pauseListening"),
                TrayMenuItem(1005, "Settings", "settings"),
                TrayMenuItem(0, "", "", separator=True),
                TrayMenuItem(1099, "Exit Aura", "exitAura"),
            ]
        )

    def _buildTrayActionMap(self) -> dict[str, Any]:
        return {
            "openAura": self.showWindow,
            "quickConversation": self.showQuickInteraction,
            "muteMicrophone": self.trayActions.muteMicrophone,
            "pauseListening": self.trayActions.pauseListening,
            "settings": self.trayActions.settings,
            "exitAura": self.trayActions.exitAura,
        }

    def _activeProviderName(self) -> str:
        manager = getattr(self.context, "llmManager", None)
        return str(getattr(manager, "activeProviderName", "") or "")

    def _providerConnected(self) -> bool:
        manager = getattr(self.context, "llmManager", None)
        return not bool(getattr(manager, "offlineMode", False))

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

    def _bubblePositionStoragePath(self) -> str:
        configPath = self._getConfigValue("bubblePositionFile", None)
        if configPath:
            return str(configPath)
        from pathlib import Path

        return str(Path.home() / ".aura" / "desktop_overlay_bubble_position.json")
