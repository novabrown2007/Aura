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


@dataclass(frozen=True)
class TileSpec:
    tile_id: int
    title: str


class BlankWindowApp:
    """Create and run the first Aura homepage shell."""

    def __init__(self, title: str = "Aura", width: int = 960, height: int = 680):
        self.title = str(title or "Aura")
        self.width = int(width or 960)
        self.height = int(height or 680)
        self.theme = Theme()
        self.root = None
        self.canvas = None
        self.sidebar_frame = None
        self.sidebar_visible = False
        self.test_frame = None
        self.test_var = None
        self._drag_offset = (0, 0)
        self._active_tile_id: int | None = None
        self._active_tile_offset = (0, 0)
        self._drag_position: tuple[int, int] | None = None
        self._tile_order = [0, 1, 2, 3]
        self._tile_specs = [
            TileSpec(0, "Tile 1"),
            TileSpec(1, "Tile 2"),
            TileSpec(2, "Tile 3"),
            TileSpec(3, "Tile 4"),
        ]
        self._grid = (
            (86, 130),
            (354, 130),
            (86, 394),
            (354, 394),
        )
        self._tile_size = (230, 220)
        self._sidebar_width = 220
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
        self.test_var = tk.StringVar(value="")
        self._create_overlay_widgets(tk)

        root.bind("<Map>", self._render)
        root.bind("<Configure>", self._render)
        root.bind("<Escape>", lambda _event: self.close())

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

    def _create_overlay_widgets(self, tk):
        root = self.root
        if root is None:
            return

        self.sidebar_frame = tk.Frame(
            root,
            bg=self.theme.panel,
            highlightbackground=self.theme.border,
            highlightthickness=1,
        )
        tk.Label(
            self.sidebar_frame,
            text="Sidebar",
            bg=self.theme.panel,
            fg=self.theme.text,
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(14, 8))
        for label in ("Home", "Widgets", "Tests"):
            tk.Label(
                self.sidebar_frame,
                text=label,
                bg=self.theme.panel,
                fg=self.theme.placeholder,
                font=("Segoe UI", 11),
                anchor="w",
            ).pack(fill="x", padx=14, pady=4)

        self.test_frame = tk.Frame(
            root,
            bg=self.theme.panel,
            highlightbackground=self.theme.border,
            highlightthickness=1,
        )
        tk.Label(
            self.test_frame,
            text="Test box",
            bg=self.theme.panel,
            fg=self.theme.placeholder,
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(8, 2))
        test_entry = tk.Entry(
            self.test_frame,
            textvariable=self.test_var,
            font=("Segoe UI", 14),
            bg=self.theme.background,
            fg=self.theme.text,
            insertbackground=self.theme.text,
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        test_entry.pack(fill="x", padx=12, pady=(0, 10))
        test_entry.bind("<Return>", self._submit_prompt)

    def _render(self, _event=None):
        canvas = self.canvas
        root = self.root
        if canvas is None or root is None:
            return

        width = max(1, root.winfo_width())
        height = max(1, root.winfo_height())
        canvas.delete("all")

        self._layout_overlay_widgets(width, height)
        self._draw_window_shell(canvas, width, height)
        self._draw_title_bar(canvas, width)
        self._draw_tiles(canvas)
        self._draw_prompt_strip(canvas, width, height)
        self._draw_sidebar(canvas, width, height)

    def _layout_overlay_widgets(self, width: int, height: int):
        if self.sidebar_frame is not None:
            if self.sidebar_visible:
                self.sidebar_frame.place(x=12, y=self._top_bar_height + 12, width=self._sidebar_width, height=height - self._top_bar_height - self._prompt_bar_height - 42)
            else:
                self.sidebar_frame.place_forget()

        if self.test_frame is not None:
            self.test_frame.place(x=72, y=height - 60, width=max(260, width - 176), height=36)

    def _draw_window_shell(self, canvas, width: int, height: int):
        self._rounded_rect(canvas, 10, 10, width - 10, height - 10, 18, fill=self.theme.panel, outline=self.theme.border, width=2)

    def _draw_title_bar(self, canvas, width: int):
        self._rounded_rect(canvas, 12, 12, width - 12, 80, 16, fill=self.theme.chrome, outline=self.theme.border, width=1)
        canvas.create_line(20, 80, width - 20, 80, fill=self.theme.border, width=1)
        self._draw_menu_icon(canvas, 32, 46, self._toggle_sidebar)
        self._draw_window_icon(canvas, width - 92, 46, self._minimize_window)
        self._draw_close_icon(canvas, width - 48, 46, self.close)

    def _draw_tiles(self, canvas):
        for slot_index, (x, y) in enumerate(self._grid):
            tile_id = self._tile_order[slot_index]
            spec = self._tile_specs[tile_id]
            if self._active_tile_id == tile_id and self._drag_position is not None:
                draw_x, draw_y = self._drag_position
                active = True
            else:
                draw_x, draw_y = x, y
                active = False
            self._draw_tile(canvas, draw_x, draw_y, spec.title, active=active)

    def _draw_tile(self, canvas, x: int, y: int, title: str, active: bool = False):
        width, height = self._tile_size
        fill = self.theme.background if not active else "#202020"
        outline = self.theme.accent if active else self.theme.border
        self._rounded_rect(canvas, x, y, x + width, y + height, 16, fill=fill, outline=outline, width=2)
        canvas.create_text(x + 20, y + 20, anchor="nw", text=title, fill=self.theme.placeholder, font=("Segoe UI", 10))

    def _draw_prompt_strip(self, canvas, width: int, height: int):
        base_y = height - self._prompt_bar_height - 16
        canvas.create_line(20, base_y, width - 20, base_y, fill=self.theme.border, width=1)
        self._draw_status_dot(canvas, 40, height - 43)
        self._rounded_rect(canvas, 72, height - 60, width - 104, height - 24, 16, fill=self.theme.panel, outline=self.theme.border, width=2)
        canvas.create_text(96, height - 42, anchor="w", text="Test box", fill=self.theme.placeholder, font=("Segoe UI", 16))
        self._draw_prompt_button(canvas, width - 52, height - 42)

    def _draw_sidebar(self, canvas, width: int, height: int):
        if not self.sidebar_visible:
            return
        x1 = 12
        y1 = self._top_bar_height + 12
        x2 = x1 + self._sidebar_width
        y2 = height - self._prompt_bar_height - 28
        self._rounded_rect(canvas, x1, y1, x2, y2, 14, fill=self.theme.panel, outline=self.theme.border, width=2)

    def _draw_status_dot(self, canvas, x: int, y: int):
        canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=self.theme.accent, outline=self.theme.accent)

    def _draw_menu_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="menu")

    def _draw_window_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="window")

    def _draw_close_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="close")

    def _draw_prompt_button(self, canvas, center_x: int, center_y: int):
        button = self._rounded_rect(
            canvas,
            center_x - 16,
            center_y - 16,
            center_x + 16,
            center_y + 16,
            9,
            fill=self.theme.chrome,
            outline=self.theme.chrome,
            width=1,
        )
        canvas.create_text(center_x, center_y - 1, text=">", fill=self.theme.text, font=("Segoe UI", 16, "bold"))
        canvas.tag_bind(button, "<Button-1>", lambda _event: self._submit_prompt())
        return button

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

    def _toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        self._render()

    def _minimize_window(self):
        return None

    def _submit_prompt(self, _event=None):
        return None

    def _bind_drag_targets(self, root, canvas):
        canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        canvas.bind("<B1-Motion>", self._on_canvas_drag)
        canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def _on_canvas_press(self, event):
        tile_id = self._hit_test_tile(event.x, event.y)
        if tile_id is None:
            return
        slot_index = self._slot_index_for_tile(tile_id)
        tile_x, tile_y = self._grid[slot_index]
        self._active_tile_id = tile_id
        self._active_tile_offset = (event.x - tile_x, event.y - tile_y)
        self._drag_position = (tile_x, tile_y)
        self._render()

    def _on_canvas_drag(self, event):
        if self._active_tile_id is None:
            return
        offset_x, offset_y = self._active_tile_offset
        self._drag_position = (event.x - offset_x, event.y - offset_y)
        self._render()

    def _on_canvas_release(self, event):
        if self._active_tile_id is None:
            return

        tile_x, tile_y = self._drag_position or (0, 0)
        tile_w, tile_h = self._tile_size
        center_x = tile_x + tile_w / 2
        center_y = tile_y + tile_h / 2
        target_slot = self._nearest_slot(center_x, center_y)
        current_slot = self._slot_index_for_tile(self._active_tile_id)

        if target_slot != current_slot:
            tile_id = self._tile_order.pop(current_slot)
            self._tile_order.insert(target_slot, tile_id)

        self._active_tile_id = None
        self._drag_position = None
        self._render()

    def _hit_test_tile(self, x: int, y: int) -> int | None:
        for slot_index, (tile_x, tile_y) in enumerate(self._grid):
            tile_id = self._tile_order[slot_index]
            if tile_x <= x <= tile_x + self._tile_size[0] and tile_y <= y <= tile_y + self._tile_size[1]:
                return tile_id
        return None

    def _slot_index_for_tile(self, tile_id: int) -> int:
        for index, current in enumerate(self._tile_order):
            if current == tile_id:
                return index
        return 0

    def _nearest_slot(self, center_x: float, center_y: float) -> int:
        best_index = 0
        best_distance = float("inf")
        for index, (slot_x, slot_y) in enumerate(self._grid):
            slot_center_x = slot_x + self._tile_size[0] / 2
            slot_center_y = slot_y + self._tile_size[1] / 2
            distance = (center_x - slot_center_x) ** 2 + (center_y - slot_center_y) ** 2
            if distance < best_distance:
                best_distance = distance
                best_index = index
        return best_index

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
