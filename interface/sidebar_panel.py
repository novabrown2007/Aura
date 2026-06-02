"""Sidebar panel rendering for the Aura shell."""

from __future__ import annotations

from .drawing import shadow_round_rect
from .theme import Theme


class SidebarPanel:
    """Render the slide-out sidebar and its controls."""

    def __init__(self, theme: Theme, width: int = 210):
        self.theme = theme
        self.width = int(width)

    def render(self, canvas, width: int, height: int, visible: bool, on_close):
        if not visible:
            return

        top = 102
        bottom = height - 148
        x1 = 24
        x2 = x1 + self.width
        shadow_round_rect(canvas, x1, top, x2, bottom, 14, fill=self.theme.panel, outline=self.theme.border, width=2)
        canvas.create_text(x1 + 16, top + 16, anchor="nw", text="Menu", fill=self.theme.text, font=("Segoe UI", 13, "bold"))
        self._draw_sidebar_close_button(canvas, x2 - 20, top + 20, on_close)
        self._draw_sidebar_item(canvas, x1 + 16, top + 56, "Home", active=True)
        self._draw_sidebar_item(canvas, x1 + 16, top + 92, "Chat", active=False)
        canvas.create_line(x1 + 16, bottom - 56, x2 - 16, bottom - 56, fill=self.theme.border, width=1)
        self._draw_sidebar_item(canvas, x1 + 16, bottom - 40, "Settings", active=False)

    def point_inside(self, x: int, y: int, width: int, height: int, visible: bool) -> bool:
        if not visible:
            return False
        left = 24
        top = 102
        right = left + self.width
        bottom = height - 148
        return left <= x <= right and top <= y <= bottom

    def _draw_sidebar_item(self, canvas, x: int, y: int, label: str, active: bool = False):
        fill = self.theme.text if active else self.theme.placeholder
        canvas.create_text(x, y, anchor="nw", text=label, fill=fill, font=("Segoe UI", 11, "bold" if active else "normal"))

    def _draw_sidebar_close_button(self, canvas, center_x: int, center_y: int, on_close):
        tag = f"sidebar_close_{center_x}_{center_y}"
        button = shadow_round_rect(
            canvas,
            center_x - 11,
            center_y - 11,
            center_x + 11,
            center_y + 11,
            7,
            fill="",
            outline=self.theme.border,
            width=1,
            tags=(tag,),
        )
        canvas.create_line(center_x - 5, center_y - 5, center_x + 5, center_y + 5, fill=self.theme.text, width=2, tags=(tag,))
        canvas.create_line(center_x - 5, center_y + 5, center_x + 5, center_y - 5, fill=self.theme.text, width=2, tags=(tag,))
        canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.itemconfigure(button, outline=self.theme.secondary_accent))
        canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.itemconfigure(button, outline=self.theme.border))
        canvas.tag_bind(tag, "<Button-1>", lambda _event: on_close())
        canvas.tag_raise(tag)
        return button
