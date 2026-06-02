"""Top bar wrapper for the Aura application shell."""

from __future__ import annotations

from .window_chrome import WindowChrome


class TopBar:
    """Expose the fixed header controls as a distinct shell component."""

    def __init__(self, chrome: WindowChrome):
        self.chrome = chrome

    def render(self, canvas, width: int, callbacks):
        self.chrome._draw_title_bar(canvas, width, callbacks)

    def point_in_control(self, x: int, y: int, width: int) -> bool:
        return self.chrome.point_in_title_bar_control(x, y, width)
