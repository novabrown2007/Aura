"""Minimal Aura homepage mockup."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    background: str = "#151515"
    panel: str = "#181818"
    border: str = "#444444"
    chrome: str = "#1b1b1b"
    text: str = "#d8d8d8"
    placeholder: str = "#767676"
    accent: str = "#8b8b8b"


class BlankWindowApp:
    """Create and run the first Aura homepage shell."""

    def __init__(self, title: str = "Aura", width: int = 960, height: int = 680):
        self.title = str(title or "Aura")
        self.width = int(width or 960)
        self.height = int(height or 680)
        self.theme = Theme()
        self.root = None
        self.canvas = None
        self.prompt_var = None
        self._drag_offset = (0, 0)
        self._top_bar_height = 70
        self._prompt_bar_height = 62

    def build(self):
        """Create the Tk root window and lay out the mock homepage."""

        try:
            import tkinter as tk
        except Exception as error:
            raise RuntimeError("Tkinter is required to open the Aura window.") from error

        root = tk.Tk()
        root.title(self.title)
        root.geometry(f"{self.width}x{self.height}")
        root.minsize(760, 520)
        root.configure(bg=self.theme.background)
        root.overrideredirect(True)

        canvas = tk.Canvas(root, bg=self.theme.background, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)

        self.root = root
        self.canvas = canvas
        self.prompt_var = tk.StringVar(value="")

        root.bind("<Map>", self._render)
        root.bind("<Configure>", self._render)
        root.bind("<Escape>", lambda _event: self.close())
        self._bind_drag_targets(root, canvas)

        self._render()
        return root

    def run(self):
        """Show the window and block until it closes."""

        root = self.root or self.build()
        root.mainloop()

    def close(self):
        """Destroy the window if it exists."""

        root = self.root
        if root is None:
            return
        try:
            root.destroy()
        finally:
            self.root = None
            self.canvas = None

    def _render(self, _event=None):
        canvas = self.canvas
        root = self.root
        if canvas is None or root is None:
            return

        width = max(1, root.winfo_width())
        height = max(1, root.winfo_height())
        canvas.delete("all")

        self._draw_window_shell(canvas, width, height)
        self._draw_title_bar(canvas, width)
        self._draw_tiles(canvas, width, height)
        self._draw_prompt_bar(canvas, width, height)

    def _draw_window_shell(self, canvas, width: int, height: int):
        self._rounded_rect(canvas, 10, 10, width - 10, height - 10, 18, fill=self.theme.panel, outline=self.theme.border, width=2)

    def _draw_title_bar(self, canvas, width: int):
        self._rounded_rect(canvas, 12, 12, width - 12, 80, 16, fill=self.theme.chrome, outline=self.theme.border, width=1)
        canvas.create_line(20, 80, width - 20, 80, fill=self.theme.border, width=1)

        self._draw_menu_icon(canvas, 32, 46, self._toggle_menu)
        self._draw_window_icon(canvas, width - 92, 46, self._minimize_window)
        self._draw_close_icon(canvas, width - 48, 46, self.close)

    def _draw_tiles(self, canvas, width: int, height: int):
        tile_width = 230
        tile_height = 220
        gap_x = 38
        gap_y = 44
        left = 86
        top = 130

        for row in range(2):
            for col in range(2):
                x1 = left + col * (tile_width + gap_x)
                y1 = top + row * (tile_height + gap_y)
                x2 = x1 + tile_width
                y2 = y1 + tile_height
                self._rounded_rect(canvas, x1, y1, x2, y2, 16, fill=self.theme.background, outline=self.theme.border, width=2)

    def _draw_prompt_bar(self, canvas, width: int, height: int):
        base_y = height - self._prompt_bar_height - 16
        canvas.create_line(20, base_y, width - 20, base_y, fill=self.theme.border, width=1)

        self._draw_status_dot(canvas, 40, height - 43)
        self._rounded_rect(canvas, 72, height - 60, width - 104, height - 24, 16, fill=self.theme.panel, outline=self.theme.border, width=2)

        if self.root is None or self.prompt_var is None:
            return

        import tkinter as tk

        entry = tk.Entry(
            self.root,
            textvariable=self.prompt_var,
            font=("Segoe UI", 14),
            bg=self.theme.panel,
            fg=self.theme.text,
            insertbackground=self.theme.text,
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        entry.insert(0, "")
        entry.bind("<Return>", lambda _event: self._submit_prompt())
        canvas.create_window(92, height - 42, anchor="w", window=entry, width=max(200, width - 220), height=28, tags=("prompt_entry",))

        button = tk.Button(
            self.root,
            text=">",
            command=self._submit_prompt,
            font=("Segoe UI", 14, "bold"),
            bg=self.theme.chrome,
            fg=self.theme.text,
            activebackground=self.theme.border,
            activeforeground=self.theme.text,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=2,
        )
        canvas.create_window(width - 52, height - 42, anchor="center", window=button, width=28, height=28, tags=("prompt_button",))

    def _draw_status_dot(self, canvas, x: int, y: int):
        canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=self.theme.accent, outline=self.theme.accent)

    def _draw_menu_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="menu")

    def _draw_window_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="window")

    def _draw_close_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="close")

    def _draw_bar_button(self, canvas, center_x: int, center_y: int, callback, kind: str):
        size = 32
        button = self._rounded_rect(
            canvas,
            center_x - size // 2,
            center_y - size // 2,
            center_x + size // 2,
            center_y + size // 2,
            9,
            fill=self.theme.chrome,
            outline=self.theme.chrome,
            width=1,
        )
        if kind == "menu":
            for offset in (-6, 0, 6):
                canvas.create_line(center_x - 7, center_y + offset, center_x + 7, center_y + offset, fill=self.theme.text, width=2)
        elif kind == "window":
            canvas.create_rectangle(center_x - 6, center_y - 7, center_x + 6, center_y + 7, outline=self.theme.text, width=2)
        else:
            canvas.create_line(center_x - 6, center_y - 6, center_x + 6, center_y + 6, fill=self.theme.text, width=2)
            canvas.create_line(center_x - 6, center_y + 6, center_x + 6, center_y - 6, fill=self.theme.text, width=2)

        canvas.tag_bind(button, "<Button-1>", lambda _event: callback())
        canvas.tag_bind(button, "<Enter>", lambda _event: canvas.itemconfigure(button, outline=self.theme.border))
        canvas.tag_bind(button, "<Leave>", lambda _event: canvas.itemconfigure(button, outline=self.theme.chrome))
        return button

    def _toggle_menu(self):
        return None

    def _minimize_window(self):
        root = self.root
        if root is not None:
            root.iconify()

    def _submit_prompt(self):
        return None

    def _bind_drag_targets(self, root, canvas):
        def start_drag(event):
            self._drag_offset = (event.x_root, event.y_root)

        def drag(event):
            offset_x, offset_y = self._drag_offset
            delta_x = event.x_root - offset_x
            delta_y = event.y_root - offset_y
            if delta_x == 0 and delta_y == 0:
                return
            root.geometry(f"+{root.winfo_x() + delta_x}+{root.winfo_y() + delta_y}")
            self._drag_offset = (event.x_root, event.y_root)

        for target in (root, canvas):
            target.bind("<ButtonPress-1>", start_drag)
            target.bind("<B1-Motion>", drag)

    @staticmethod
    def _rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=36, **kwargs)
