"""Overlay component package for the Aura application shell."""

from .confirmation_dialog import ConfirmationDialog
from .future_modals import FutureModals
from .notification_panel import NotificationPanel
from .settings_overlay import SettingsOverlay
from .widget_editor_overlay import WidgetEditorOverlay

__all__ = [
    "ConfirmationDialog",
    "FutureModals",
    "NotificationPanel",
    "SettingsOverlay",
    "WidgetEditorOverlay",
]
