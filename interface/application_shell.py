"""High-level Aura application shell composition."""

from __future__ import annotations

from .content_area import ContentArea
from .footer_input import FooterInput
from .overlay_layer import OverlayLayer
from .sidebar_panel import SidebarPanel
from .top_bar import TopBar
from .window_chrome import ChromeCallbacks, WindowChrome


class ApplicationShell:
    """Compose the fixed shell regions and the switchable content area."""

    def __init__(self, chrome: WindowChrome, sidebar: SidebarPanel, content_area: ContentArea, footer_input: FooterInput, overlay_layer: OverlayLayer):
        self.chrome = chrome
        self.top_bar = TopBar(chrome)
        self.sidebar = sidebar
        self.content_area = content_area
        self.footer_input = footer_input
        self.overlay_layer = overlay_layer

    def create_footer_input(self, root, tk, submit_callback):
        return self.footer_input.create(root, tk, submit_callback)

    def layout(self, width: int, height: int):
        self.footer_input.layout(width, height)

    def render(self, canvas, width: int, height: int, callbacks: ChromeCallbacks, sidebar_visible: bool):
        self.chrome._draw_window_shell(canvas, width, height)
        self.top_bar.render(canvas, width, callbacks)
        content_bounds = self.content_bounds(width, height, sidebar_visible)
        self.content_area.render(canvas, width, height, self.chrome.theme, sidebar_visible)
        self.sidebar.render(
            canvas,
            width,
            height,
            sidebar_visible,
            callbacks.close_sidebar,
            callbacks.settings,
            callbacks.home,
            callbacks.chat,
            self.content_area.currentPageName(),
        )
        self.footer_input.render(canvas, width, height, callbacks)
        self.overlay_layer.render(canvas, self.footer_input, content_bounds)

    def point_in_title_bar_control(self, x: int, y: int, width: int) -> bool:
        return self.top_bar.point_in_control(x, y, width)

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        return self.content_area.content_bounds(width, height, sidebar_visible)

    def set_prompt_hover(self, canvas, x: int | None, y: int | None):
        # Prompt hover is a footer concern; the overlay layer stays a placeholder.
        self.footer_input.apply_hover(canvas, self.footer_input.is_hovered(x, y))
