"""Overlay layer placeholder for future transient UI content."""

from __future__ import annotations

from .drawing import shadow_round_rect
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
        self.settings_visible = False
        self._settings_panel_bounds = (0, 0, 0, 0)
        self._settings_close_bounds = (0, 0, 0, 0)

    def update_prompt_hover(self, is_hovered: bool):
        # Placeholder hook: overlay state will be managed here when real modals exist.
        _ = is_hovered

    def show_settings(self):
        # Placeholder modal toggle for the settings overlay.
        self.settings_visible = True

    def hide_settings(self):
        # Placeholder modal toggle for the settings overlay.
        self.settings_visible = False

    def toggle_settings(self):
        # Placeholder modal toggle for the settings overlay.
        self.settings_visible = not self.settings_visible

    def render(self, canvas, footer_input, content_bounds=None):
        # Render a blank centered modal frame when settings is toggled on.
        if self.settings_visible:
            width = max(1, int(canvas.winfo_width() or 0))
            if content_bounds is None:
                content_bounds = {"left": 36, "right": width - 36, "top": 102, "bottom": max(102, canvas.winfo_height() - 148)}
            panel_width = min(680, max(440, width - 220))
            panel_height = min(520, max(320, content_bounds["bottom"] - content_bounds["top"] - 40))
            left = max(content_bounds["left"], (width - panel_width) // 2)
            top = max(content_bounds["top"] + 20, (content_bounds["top"] + content_bounds["bottom"] - panel_height) // 2)
            self._settings_panel_bounds = (left, top, left + panel_width, top + panel_height)
            self._settings_close_bounds = (left + panel_width - 40, top + 16, left + panel_width - 16, top + 40)
            canvas.create_rectangle(
                content_bounds["left"],
                content_bounds["top"],
                content_bounds["right"],
                content_bounds["bottom"],
                fill="#000000",
                outline="",
                stipple="gray50",
            )
            shadow_round_rect(canvas, left, top, left + panel_width, top + panel_height, 18, fill=self.settings_overlay_bg(), outline=self.settings_overlay_border(), width=2)
            self._draw_settings_close_button(canvas, left + panel_width - 28, top + 28)
            # Intentionally blank: content will be added later.
        _ = footer_input
        return None

    def handle_press(self, x: int, y: int, width: int, height: int) -> bool:
        # Placeholder modal interaction: only the close button is interactive for now.
        _ = width
        _ = height
        if not self.settings_visible:
            return False
        x1, y1, x2, y2 = self._settings_close_bounds
        if x1 <= x <= x2 and y1 <= y <= y2:
            self.hide_settings()
            return True
        return False

    def settings_overlay_bg(self) -> str:
        return self.settings_overlay_background

    def settings_overlay_border(self) -> str:
        return self.settings_overlay_outline

    @property
    def settings_overlay_background(self) -> str:
        return "#111722"

    @property
    def settings_overlay_outline(self) -> str:
        return "#4d5f6f"

    def _draw_settings_close_button(self, canvas, center_x: int, center_y: int):
        # Placeholder close control for the settings overlay.
        tag = f"settings_close_{center_x}_{center_y}"
        button = shadow_round_rect(
            canvas,
            center_x - 12,
            center_y - 12,
            center_x + 12,
            center_y + 12,
            7,
            fill="",
            outline=self.settings_overlay_border(),
            width=1,
            tags=(tag,),
        )
        canvas.create_line(center_x - 5, center_y - 5, center_x + 5, center_y + 5, fill=self.settings_overlay_border(), width=2, tags=(tag,))
        canvas.create_line(center_x - 5, center_y + 5, center_x + 5, center_y - 5, fill=self.settings_overlay_border(), width=2, tags=(tag,))
        canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.itemconfigure(button, outline=self.settings_overlay_outline_hover()))
        canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.itemconfigure(button, outline=self.settings_overlay_border()))
        return button

    def settings_overlay_outline_hover(self) -> str:
        return "#7b8ea0"
