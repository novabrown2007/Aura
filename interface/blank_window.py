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

    def __init__(self, title: str = "Aura", width: int = 960, height: int = 740):
        self.title = str(title or "Aura")
        self.width = int(width or 960)
        self.height = int(height or 680)
        self.theme = Theme()
        self.root = None
        self.canvas = None
        self.test_frame = None
        self.test_var = None
        self.test_value = ""
        self.sidebar_visible = False
        self._drag_offset = (0, 0)
        self._active_tile_id: int | None = None
        self._active_tile_offset = (0, 0)
        self._drag_position: tuple[int, int] | None = None
        self._tile_order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        self._tile_specs = [
            TileSpec(0, "Tile 1"),
            TileSpec(1, "Tile 2"),
            TileSpec(2, "Tile 3"),
            TileSpec(3, "Tile 4"),
            TileSpec(4, "Tile 5"),
            TileSpec(5, "Tile 6"),
            TileSpec(6, "Tile 7"),
            TileSpec(7, "Tile 8"),
            TileSpec(8, "Tile 9"),
            TileSpec(9, "Tile 10"),
            TileSpec(10, "Tile 11"),
            TileSpec(11, "Tile 12"),
        ]
        self._tile_size = (130, 110)
        self._tile_columns = 4
        self._tile_rows = 3
        self._tile_gap = (16, 18)
        self._top_bar_rect = (12, 12, 948, 80)
        self._shell_padding = 10
        self._sidebar_width = 210
        self._content_top = 102
        self._content_bottom_margin = 138
        self._prompt_height = 58

    def build(self):
        """Create the Tk root window and lay out the mock homepage."""

        try:
            import tkinter as tk
        except Exception as error:
            raise RuntimeError("Tkinter is required to open the Aura window.") from error

        root = tk.Tk()
        root.title(self.title)
        root.geometry(f"{self.width}x{self.height}")
        root.minsize(760, 580)
        root.configure(bg=self.theme.background)
        root.overrideredirect(True)

        canvas = tk.Canvas(root, bg=self.theme.background, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)

        self.root = root
        self.canvas = canvas
        self.test_var = tk.StringVar(value="")
        self._create_test_box(tk)

        root.bind("<Map>", self._render)
        root.bind("<Configure>", self._render)
        root.bind("<Escape>", lambda _event: self.close())

        self._bind_drag_targets(canvas)
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

    def _create_test_box(self, tk):
        root = self.root
        if root is None:
            return

        self.test_frame = tk.Frame(
            root,
            bg=self.theme.panel,
            highlightbackground=self.theme.border,
            highlightthickness=1,
        )
        entry = tk.Entry(
            self.test_frame,
            textvariable=self.test_var,
            font=("Segoe UI", 13),
            bg=self.theme.background,
            fg=self.theme.placeholder,
            insertbackground=self.theme.text,
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        entry.pack(fill="both", expand=True, padx=12, pady=10)
        entry.insert(0, "Test box")
        entry.bind("<FocusIn>", self._clear_test_placeholder)
        entry.bind("<FocusOut>", self._restore_test_placeholder)
        entry.bind("<Return>", self._submit_prompt)

    def _render(self, _event=None):
        canvas = self.canvas
        root = self.root
        if canvas is None or root is None:
            return

        width = max(1, root.winfo_width())
        height = max(1, root.winfo_height())
        canvas.delete("all")

        self._layout_test_box(width, height)
        self._draw_window_shell(canvas, width, height)
        self._draw_title_bar(canvas, width)
        self._draw_tiles(canvas, width, height)
        self._draw_sidebar(canvas, width, height)
        self._draw_prompt_strip(canvas, width, height)

    def _layout_test_box(self, width: int, height: int):
        if self.test_frame is None:
            return
        frame_width = min(720, max(280, width - 240))
        frame_x = 72
        frame_y = height - 54
        self.test_frame.place(x=frame_x, y=frame_y, width=frame_width, height=32)

    def _draw_window_shell(self, canvas, width: int, height: int):
        self._rounded_rect(canvas, 10, 10, width - 10, height - 10, 18, fill=self.theme.panel, outline=self.theme.border, width=2)

    def _draw_title_bar(self, canvas, width: int):
        self._rounded_rect(canvas, 12, 12, width - 12, 80, 16, fill=self.theme.chrome, outline=self.theme.border, width=1)
        canvas.create_line(20, 80, width - 20, 80, fill=self.theme.border, width=1)
        self._draw_menu_icon(canvas, 32, 46, self._toggle_sidebar)
        self._draw_window_icon(canvas, width - 92, 46, self._noop)
        self._draw_close_icon(canvas, width - 48, 46, self.close)

    def _draw_tiles(self, canvas, width: int, height: int):
        available = self._content_bounds(width, height)
        tile_size = self._tile_dimensions(available)
        tile_positions = self._tile_positions(available["left"], available["top"], available["right"], available["bottom"], tile_size)

        for slot_index, (x, y) in enumerate(tile_positions):
            tile_id = self._tile_order[slot_index]
            spec = self._tile_specs[tile_id]
            if self._active_tile_id == tile_id and self._drag_position is not None:
                draw_x, draw_y = self._drag_position
                active = True
            else:
                draw_x, draw_y = x, y
                active = False
            self._draw_tile(canvas, draw_x, draw_y, spec.title, tile_size, active=active)

    def _draw_tile(self, canvas, x: int, y: int, title: str, tile_size: tuple[int, int], active: bool = False):
        width, height = tile_size
        fill = self.theme.background if not active else "#202020"
        outline = self.theme.accent if active else self.theme.border
        self._rounded_rect(canvas, x, y, x + width, y + height, 16, fill=fill, outline=outline, width=2)
        canvas.create_text(x + 20, y + 20, anchor="nw", text=title, fill=self.theme.placeholder, font=("Segoe UI", 10))

    def _draw_sidebar(self, canvas, width: int, height: int):
        if not self.sidebar_visible:
            return

        top = self._content_top
        bottom = height - self._content_bottom_margin
        x1 = 24
        x2 = x1 + self._sidebar_width
        self._rounded_rect(canvas, x1, top, x2, bottom, 14, fill=self.theme.panel, outline=self.theme.border, width=2)
        canvas.create_text(x1 + 16, top + 16, anchor="nw", text="Menu", fill=self.theme.text, font=("Segoe UI", 13, "bold"))
        self._draw_sidebar_item(canvas, x1 + 16, top + 56, "Home", active=True)
        self._draw_sidebar_item(canvas, x1 + 16, top + 92, "Chat", active=False)
        canvas.create_line(x1 + 16, bottom - 56, x2 - 16, bottom - 56, fill=self.theme.border, width=1)
        self._draw_sidebar_item(canvas, x1 + 16, bottom - 40, "Settings", active=False)

    def _draw_sidebar_item(self, canvas, x: int, y: int, label: str, active: bool = False):
        fill = self.theme.text if active else self.theme.placeholder
        canvas.create_text(x, y, anchor="nw", text=label, fill=fill, font=("Segoe UI", 11, "bold" if active else "normal"))

    def _draw_prompt_strip(self, canvas, width: int, height: int):
        top = height - self._prompt_height - 12
        canvas.create_line(20, top, width - 20, top, fill=self.theme.border, width=1)
        self._draw_status_dot(canvas, 40, height - 42)
        self._draw_prompt_button(canvas, width - 52, height - 39)

    def _draw_status_dot(self, canvas, x: int, y: int):
        canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=self.theme.accent, outline=self.theme.accent)

    def _draw_menu_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="menu")

    def _draw_window_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="window")

    def _draw_close_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="close")

    def _draw_prompt_button(self, canvas, center_x: int, center_y: int):
        tag = f"prompt_button_{center_x}_{center_y}"
        button = self._rounded_rect(
            canvas,
            center_x - 16,
            center_y - 16,
            center_x + 16,
            center_y + 16,
            9,
            fill="",
            outline="",
            width=1,
            tags=(tag,),
        )
        canvas.create_text(
            center_x,
            center_y - 1,
            text=">",
            fill=self.theme.text,
            font=("Segoe UI", 16, "bold"),
            tags=(tag,),
        )
        canvas.tag_bind(tag, "<Button-1>", lambda _event: self._submit_prompt())
        canvas.tag_raise(tag)
        return button

    def _draw_bar_button(self, canvas, center_x: int, center_y: int, callback, kind: str):
        size = 32
        tag = f"bar_button_{kind}_{center_x}_{center_y}"
        button = self._rounded_rect(
            canvas,
            center_x - size // 2,
            center_y - size // 2,
            center_x + size // 2,
            center_y + size // 2,
            9,
            fill="",
            outline="",
            width=1,
            tags=(tag,),
        )
        if kind == "menu":
            for offset in (-6, 0, 6):
                canvas.create_line(
                    center_x - 7,
                    center_y + offset,
                    center_x + 7,
                    center_y + offset,
                    fill=self.theme.text,
                    width=2,
                    tags=(tag,),
                )
        elif kind == "window":
            canvas.create_rectangle(
                center_x - 6,
                center_y - 7,
                center_x + 6,
                center_y + 7,
                outline=self.theme.text,
                width=2,
                tags=(tag,),
            )
        else:
            canvas.create_line(
                center_x - 6,
                center_y - 6,
                center_x + 6,
                center_y + 6,
                fill=self.theme.text,
                width=2,
                tags=(tag,),
            )
            canvas.create_line(
                center_x - 6,
                center_y + 6,
                center_x + 6,
                center_y - 6,
                fill=self.theme.text,
                width=2,
                tags=(tag,),
            )

        canvas.tag_bind(tag, "<Button-1>", lambda _event: callback())
        canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.itemconfigure(button, outline=self.theme.border))
        canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.itemconfigure(button, outline=""))
        canvas.tag_raise(tag)
        return button

    def _toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        self._render()

    def _noop(self):
        return None

    def _submit_prompt(self, _event=None):
        if self.test_var is not None:
            self.test_value = str(self.test_var.get() or "").strip()
        return None

    def _clear_test_placeholder(self, event=None):
        widget = getattr(event, "widget", None)
        if widget is None:
            return
        if widget.get().strip() == "Test box":
            widget.delete(0, "end")
            widget.configure(fg=self.theme.text)

    def _restore_test_placeholder(self, event=None):
        widget = getattr(event, "widget", None)
        if widget is None:
            return
        if not widget.get().strip():
            widget.insert(0, "Test box")
            widget.configure(fg=self.theme.placeholder)

    def _bind_drag_targets(self, canvas):
        canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        canvas.bind("<B1-Motion>", self._on_canvas_drag)
        canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

    def _on_canvas_press(self, event):
        if self.sidebar_visible and not self._point_in_sidebar(event.x, event.y) and not self._point_in_title_bar_control(event.x, event.y):
            self.sidebar_visible = False
            self._render()
            return
        tile_id = self._hit_test_tile(event.x, event.y)
        if tile_id is None:
            return
        slot_index = self._slot_index_for_tile(tile_id)
        bounds = self._content_bounds(self.root.winfo_width(), self.root.winfo_height())
        tile_size = self._tile_dimensions(bounds)
        tile_x, tile_y = self._tile_positions(bounds["left"], bounds["top"], bounds["right"], bounds["bottom"], tile_size)[slot_index]
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
        bounds = self._content_bounds(self.root.winfo_width(), self.root.winfo_height())
        tile_w, tile_h = self._tile_dimensions(bounds)
        center_x = tile_x + tile_w / 2
        center_y = tile_y + tile_h / 2
        target_slot = self._nearest_slot(center_x, center_y, bounds, (tile_w, tile_h))
        current_slot = self._slot_index_for_tile(self._active_tile_id)

        if target_slot != current_slot:
            tile_id = self._tile_order.pop(current_slot)
            self._tile_order.insert(target_slot, tile_id)

        self._active_tile_id = None
        self._drag_position = None
        self._render()

    def _point_in_sidebar(self, x: int, y: int) -> bool:
        if not self.sidebar_visible or self.root is None:
            return False
        bounds = self._content_bounds(self.root.winfo_width(), self.root.winfo_height())
        left = 24
        top = self._content_top
        right = left + self._sidebar_width
        bottom = bounds["bottom"]
        return left <= x <= right and top <= y <= bottom

    def _point_in_title_bar_control(self, x: int, y: int) -> bool:
        if self.root is None:
            return False
        width = self.root.winfo_width()
        return (
            16 <= x <= 48 and 30 <= y <= 62
        ) or (
            width - 108 <= x <= width - 76 and 30 <= y <= 62
        ) or (
            width - 64 <= x <= width - 32 and 30 <= y <= 62
        )

    def _content_bounds(self, width: int, height: int) -> dict[str, int]:
        left = 86
        right = width - 86
        top = self._content_top
        bottom = height - self._content_bottom_margin
        if self.sidebar_visible:
            left = 24 + self._sidebar_width + 28
        return {"left": left, "right": right, "top": top, "bottom": bottom}

    def _tile_dimensions(self, bounds: dict[str, int]) -> tuple[int, int]:
        tile_w_max, tile_h_max = self._tile_size
        avail_w = max(0, bounds["right"] - bounds["left"])
        avail_h = max(0, bounds["bottom"] - bounds["top"])
        gap_x, gap_y = self._tile_gap
        tile_w = min(tile_w_max, max(120, (avail_w - gap_x * (self._tile_columns - 1)) // self._tile_columns))
        tile_h = min(tile_h_max, max(100, (avail_h - gap_y * (self._tile_rows - 1)) // self._tile_rows))
        return int(tile_w), int(tile_h)

    def _tile_positions(self, left: int, top: int, right: int, bottom: int, tile_size: tuple[int, int]) -> list[tuple[int, int]]:
        tile_w, tile_h = tile_size
        gap_x, gap_y = self._tile_gap
        avail_w = max(tile_w, right - left)
        avail_h = max(tile_h, bottom - top)
        grid_w = tile_w * self._tile_columns + gap_x * (self._tile_columns - 1)
        grid_h = tile_h * self._tile_rows + gap_y * (self._tile_rows - 1)
        start_x = left + max(0, (avail_w - grid_w) // 2)
        start_y = top + max(0, (avail_h - grid_h) // 2)
        if self.sidebar_visible:
            start_x = left
        positions = []
        for row in range(self._tile_rows):
            for col in range(self._tile_columns):
                positions.append((start_x + col * (tile_w + gap_x), start_y + row * (tile_h + gap_y)))
        return positions

    def _hit_test_tile(self, x: int, y: int) -> int | None:
        bounds = self._content_bounds(self.root.winfo_width(), self.root.winfo_height())
        tile_size = self._tile_dimensions(bounds)
        positions = self._tile_positions(bounds["left"], bounds["top"], bounds["right"], bounds["bottom"], tile_size)
        for slot_index, (tile_x, tile_y) in enumerate(positions):
            tile_id = self._tile_order[slot_index]
            if tile_x <= x <= tile_x + tile_size[0] and tile_y <= y <= tile_y + tile_size[1]:
                return tile_id
        return None

    def _slot_index_for_tile(self, tile_id: int) -> int:
        for index, current in enumerate(self._tile_order):
            if current == tile_id:
                return index
        return 0

    def _nearest_slot(self, center_x: float, center_y: float, bounds: dict[str, int], tile_size: tuple[int, int]) -> int:
        positions = self._tile_positions(bounds["left"], bounds["top"], bounds["right"], bounds["bottom"], tile_size)
        best_index = 0
        best_distance = float("inf")
        for index, (slot_x, slot_y) in enumerate(positions):
            slot_center_x = slot_x + tile_size[0] / 2
            slot_center_y = slot_y + tile_size[1] / 2
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
