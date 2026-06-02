"""Footer input wrapper for the Aura application shell."""

from __future__ import annotations

from .window_chrome import WindowChrome


class FooterInput:
    """Expose the bottom input strip as a distinct shell component."""

    def __init__(self, chrome: WindowChrome):
        self.chrome = chrome

    def create(self, root, tk):
        return self.chrome.create_prompt_entry(root, tk)

    def layout(self, width: int, height: int):
        self.chrome.layout_prompt_entry(width, height)

    def render(self, canvas, width: int, height: int, callbacks):
        self.chrome._draw_prompt_strip(canvas, width, height, callbacks)

    def apply_hover(self, canvas, hovered: bool):
        self.chrome.apply_prompt_hover(canvas, hovered)

    def is_hovered(self, x: int | None, y: int | None) -> bool:
        return self.chrome.prompt_button_hovered(x, y)
