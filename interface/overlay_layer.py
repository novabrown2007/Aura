"""Overlay layer placeholder for future transient UI content."""

from __future__ import annotations

from .overlays import ConfirmationDialog, FutureModals, NotificationPanel, SettingsOverlay, WidgetEditorOverlay


class OverlayLayer:
    """Stub container for overlay components that will be filled in later."""

    def __init__(self):
        # These are structural placeholders so the overlay tree exists now.
        self.settings_overlay = SettingsOverlay()
        self.notification_panel = NotificationPanel()
        self.confirmation_dialog = ConfirmationDialog()
        self.widget_editor_overlay = WidgetEditorOverlay()
        self.future_modals = FutureModals()

    def update_prompt_hover(self, is_hovered: bool):
        # Placeholder hook: overlay state will be managed here when real modals exist.
        _ = is_hovered

    def render(self, canvas, footer_input):
        # Placeholder render pass: the overlay stack is intentionally empty for now.
        _ = canvas
        _ = footer_input
        return None
