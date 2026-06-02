"""Application controller for the Aura window runtime."""

from __future__ import annotations

import queue
import sys
from pathlib import Path

from .application_shell import ApplicationShell
from .assets import SpriteStore
from .content_area import ContentArea
from .footer_input import FooterInput
from .overlay_layer import OverlayLayer
from .page_manager import PageManager
from .sidebar_panel import SidebarPanel
from .theme import Theme
from .window_chrome import ChromeCallbacks, WindowChrome


class AuraWindowApp:
    """Open the Tk window, route events, and manage the run loop."""

    def __init__(self, title: str = "Aura", width: int = 960, height: int = 820):
        self.title = str(title or "Aura")
        self.width = int(width or 960)
        self.height = int(height or 680)
        self.theme = Theme()
        self.root = None
        self.canvas = None
        self._tk = None
        self.sidebar_visible = False
        self._prompt_hovered = False
        self._tray = None
        self._tray_commands: queue.Queue[str] = queue.Queue()
        self._asset_dir = self._resolve_asset_dir()
        self._sprite_crop_boxes = {
            "Sidebar icon.png": (256, 480, 768, 992),
            "Home icon.png": (256, 480, 768, 992),
            "Close icon.png": (256, 480, 768, 992),
            "Inactive Notification icon.png": (256, 448, 768, 960),
            "Active Notification icon.png": (256, 448, 768, 960),
            "Send button icon.png": (384, 384, 896, 896),
        }
        self._closing = False
        self.sprite_store = None
        self.chrome = None
        self.shell = None

    def _resolve_asset_dir(self) -> Path:
        frozen_root = getattr(sys, "_MEIPASS", None)
        if frozen_root:
            bundled_assets = Path(frozen_root) / "assets"
            if bundled_assets.exists():
                return bundled_assets

        project_assets = Path(__file__).resolve().parents[1] / "assets"
        if project_assets.exists():
            return project_assets

        return project_assets

    def build(self, start_hidden: bool = False):
        """Create the Tk root window and lay out the shell."""

        try:
            import tkinter as tk
        except Exception as error:
            raise RuntimeError("Tkinter is required to open the Aura window.") from error

        root = tk.Tk()
        root.title(self.title)
        root.geometry(f"{self.width}x{self.height}")
        root.minsize(760, 640)
        root.resizable(True, True)
        root.configure(bg=self.theme.background)
        if start_hidden:
            root.withdraw()

        canvas = tk.Canvas(root, bg=self.theme.background, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)

        self.root = root
        self.canvas = canvas
        self._tk = tk
        self.sprite_store = SpriteStore(self._asset_dir, tk)
        self.sprite_store.load()
        self.chrome = WindowChrome(self.theme, self.sprite_store, self._sprite_crop_boxes)
        content_area = ContentArea(PageManager())
        self.shell = ApplicationShell(
            chrome=self.chrome,
            sidebar=SidebarPanel(self.theme, width=210),
            content_area=content_area,
            footer_input=FooterInput(self.chrome),
            overlay_layer=OverlayLayer(),
        )
        self.shell.create_footer_input(root, tk)

        root.bind("<Map>", self._render)
        root.bind("<Configure>", self._render)
        self._bind_drag_targets(canvas)
        canvas.bind("<Motion>", self._on_canvas_motion)
        canvas.bind("<Leave>", self._on_canvas_leave)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._render()
        return root

    def run(self):
        """Show the window and block until it closes."""

        root = self.root or self.build()
        root.mainloop()
        return 1

    def run_in_tray(self):
        """Start the window hidden and expose it through a tray icon."""

        root = self.root or self.build(start_hidden=False)
        tray_started = False
        if self._tray is None:
            tray_started = self._start_tray()
        if tray_started:
            root.withdraw()
            root.after(100, self._poll_tray_commands)
        root.mainloop()
        return 1

    def close(self):
        """Destroy the window if it exists."""

        if self._closing:
            return
        self._closing = True

        tray = self._tray
        if tray is not None:
            tray.stop()
            self._tray = None

        root = self.root
        if root is None:
            self._closing = False
            return
        if self.sprite_store is not None:
            self.sprite_store.clear()

        def finalize_close():
            try:
                if root.winfo_exists():
                    root.destroy()
            finally:
                self.root = None
                self.canvas = None
                self._tk = None
                if self.chrome is not None:
                    self.chrome.test_frame = None
                    self.chrome.test_var = None
                    self.chrome._prompt_button_item = None
                    self.chrome._prompt_button_bounds = (0, 0, 0, 0)
                self._closing = False

        try:
            if root.winfo_exists():
                root.after(0, finalize_close)
            else:
                finalize_close()
        except Exception:
            finalize_close()

    def _render(self, _event=None):
        canvas = self.canvas
        root = self.root
        chrome = self.chrome
        if canvas is None or root is None or chrome is None:
            return

        try:
            width = max(1, root.winfo_width())
            height = max(1, root.winfo_height())
            canvas.delete("all")
        except Exception:
            return

        shell = self.shell
        if shell is None:
            return

        shell.layout(width, height)
        callbacks = ChromeCallbacks(
            toggle_sidebar=self._toggle_sidebar,
            home=self._set_home_page,
            window=self._noop,
            close=self.close,
            submit_prompt=self._submit_prompt,
            close_sidebar=self._close_sidebar,
        )
        shell.render(canvas, width, height, callbacks, self.sidebar_visible)

    def _bind_drag_targets(self, canvas):
        canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        canvas.bind("<B1-Motion>", self._on_canvas_drag)
        canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def _on_canvas_motion(self, event):
        if self.shell is None:
            return
        if self.canvas is not None:
            self.shell.set_prompt_hover(self.canvas, event.x, event.y)

    def _on_canvas_leave(self, _event):
        if self.canvas is not None and self.shell is not None:
            self.shell.set_prompt_hover(self.canvas, None, None)

    def _on_canvas_press(self, event):
        if self.root is None or self.shell is None:
            return
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if self.sidebar_visible and not self.shell.sidebar.point_inside(event.x, event.y, width, height, self.sidebar_visible) and not self.shell.point_in_title_bar_control(event.x, event.y, width):
            self.sidebar_visible = False
            self._render()
            return
        if self.shell.point_in_title_bar_control(event.x, event.y, width):
            return
        if self.shell.content_area.handle_press(event.x, event.y, width, height, self.sidebar_visible):
            self._render()

    def _on_canvas_drag(self, event):
        if self.root is None:
            return
        if self.shell is not None and self.shell.content_area.handle_drag(event.x, event.y, self.root.winfo_width(), self.root.winfo_height(), self.sidebar_visible):
            self._render()

    def _on_canvas_release(self, event):
        if self.root is None:
            return
        if self.shell is not None and self.shell.content_area.handle_release(event.x, event.y, self.root.winfo_width(), self.root.winfo_height(), self.sidebar_visible):
            self._render()

    def _toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        self._render()

    def _close_sidebar(self):
        if not self.sidebar_visible:
            return
        self.sidebar_visible = False
        self._render()

    def _set_home_page(self):
        if self.shell is None:
            return
        self.shell.content_area.setPage("home")
        self._render()

    def _noop(self):
        return None

    def _submit_prompt(self, _event=None):
        if self.shell is not None:
            self.shell.footer_input.chrome._submit_prompt()
        return None

    def _start_tray(self):
        try:
            from .windows_tray import WindowsTrayIcon
        except Exception:
            return False

        def request_show():
            self._tray_commands.put("show")

        try:
            self._tray = WindowsTrayIcon(self.title, request_show)
            if not self._tray.start():
                self._tray = None
                return False
        except Exception:
            self._tray = None
            return False
        return True

    def _poll_tray_commands(self):
        root = self.root
        if root is None:
            return

        while True:
            try:
                command = self._tray_commands.get_nowait()
            except queue.Empty:
                break

            if command == "show":
                self._show_window()

        root.after(100, self._poll_tray_commands)

    def _show_window(self):
        root = self.root
        if root is None:
            return
        root.deiconify()
        root.lift()
        root.focus_force()
        self._render()


BlankWindowApp = AuraWindowApp
