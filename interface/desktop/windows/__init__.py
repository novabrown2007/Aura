"""Windows-specific desktop presence layer for Aura."""

from interface.desktop.windows.handlers.overlayEventHandler import OverlayEventHandler
from interface.desktop.windows.lifecycle.shutdownManager import ShutdownManager
from interface.desktop.windows.lifecycle.windowLifecycleManager import WindowLifecycleManager
from interface.desktop.windows.notifications.desktopNotificationManager import DesktopNotificationManager
from interface.desktop.windows.overlay.assistantBubble import AssistantBubble
from interface.desktop.windows.overlay.overlayAnimator import OverlayAnimator
from interface.desktop.windows.overlay.overlayManager import OverlayManager
from interface.desktop.windows.overlay.overlayPositionManager import OverlayPositionManager
from interface.desktop.windows.overlay.overlayStateManager import OverlayStateManager
from interface.desktop.windows.overlay.overlayWindow import OverlayWindow
from interface.desktop.windows.status.assistantStatusIndicator import AssistantStatusIndicator
from interface.desktop.windows.status.connectionIndicator import ConnectionIndicator
from interface.desktop.windows.status.micStateIndicator import MicStateIndicator
from interface.desktop.windows.status.processingIndicator import ProcessingIndicator
from interface.desktop.windows.tray.systemTrayManager import SystemTrayManager

__all__ = [
    "AssistantBubble",
    "AssistantStatusIndicator",
    "ConnectionIndicator",
    "DesktopNotificationManager",
    "MicStateIndicator",
    "OverlayAnimator",
    "OverlayEventHandler",
    "OverlayManager",
    "OverlayPositionManager",
    "OverlayStateManager",
    "OverlayWindow",
    "ProcessingIndicator",
    "ShutdownManager",
    "SystemTrayManager",
    "WindowLifecycleManager",
]

