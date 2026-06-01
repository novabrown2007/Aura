"""Data models for Aura's Windows desktop presence layer."""

from interface.desktop.windows.models.assistantStatus import AssistantStatus
from interface.desktop.windows.models.overlayNotification import OverlayNotification
from interface.desktop.windows.models.overlayPosition import OverlayPosition
from interface.desktop.windows.models.overlayState import OverlayState

__all__ = [
    "AssistantStatus",
    "OverlayNotification",
    "OverlayPosition",
    "OverlayState",
]

