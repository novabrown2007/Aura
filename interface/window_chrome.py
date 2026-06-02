"""Window header, footer, and top-level controls for Aura."""

from __future__ import annotations

from dataclasses import dataclass

from .drawing import shadow_round_rect, rounded_rect
from .theme import Theme


@dataclass
class ChromeCallbacks:
    toggle_sidebar: callable
    home: callable
    chat: callable
    window: callable
    close: callable
    close_sidebar: callable
    settings: callable
    submit_prompt: callable


class WindowChrome:
    """Draw and manage the fixed header/footer chrome."""

    FOOTER_HEIGHT = 88
    FOOTER_MARGIN = 12
    FOOTER_INPUT_OFFSET_Y = 14

    def __init__(self, theme: Theme, sprite_store, sprite_crop_boxes: dict[str, tuple[int, int, int, int]]):
        self.theme = theme
        self.sprite_store = sprite_store
        self.sprite_crop_boxes = sprite_crop_boxes
        self.test_frame = None
        self.test_entry = None
        self.test_var = None
        self.test_placeholder = None
        self.test_value = ""
        self._prompt_button_item = None
        self._prompt_button_bounds = (0, 0, 0, 0)

    def create_prompt_entry(self, root, tk, submit_callback):
        self.test_frame = tk.Frame(
            root,
            bg=self.theme.panel,
            highlightbackground=self.theme.border,
            highlightthickness=1,
        )
        self.test_var = tk.StringVar(value="")
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
        placeholder = tk.Label(
            self.test_frame,
            text="Ask Aura anything...",
            font=("Segoe UI", 13),
            bg=self.theme.background,
            fg=self.theme.placeholder,
            bd=0,
            highlightthickness=0,
        )
        placeholder.place(x=16, rely=0.5, anchor="w")
        placeholder.bind("<Button-1>", self._focus_prompt_entry)
        self.test_placeholder = placeholder
        self.test_var.trace_add("write", self._sync_test_placeholder)
        entry.bind("<FocusIn>", self._sync_test_placeholder)
        entry.bind("<FocusOut>", self._sync_test_placeholder)
        entry.bind("<KeyRelease>", self._sync_test_placeholder)
        entry.bind("<Return>", lambda _event=None: submit_callback())
        self.test_entry = entry
        self._sync_test_placeholder()
        return self.test_frame

    def layout_prompt_entry(self, width: int, height: int):
        if self.test_frame is None:
            return
        frame_width = min(860, max(400, width - 340))
        frame_height = min(64, max(44, height // 12))
        frame_x = max(36, (width - frame_width) // 2)
        prompt_top = height - self.FOOTER_HEIGHT - self.FOOTER_MARGIN
        frame_y = prompt_top + self.FOOTER_INPUT_OFFSET_Y
        self.test_frame.place(x=frame_x, y=frame_y, width=frame_width, height=frame_height)

    def bind_canvas(self, canvas):
        canvas.bind("<Motion>", self._on_canvas_motion)
        canvas.bind("<Leave>", self._on_canvas_leave)

    def render(self, canvas, width: int, height: int, callbacks: ChromeCallbacks):
        self._draw_window_shell(canvas, width, height)
        self._draw_title_bar(canvas, width, callbacks)
        self._draw_prompt_strip(canvas, width, height, callbacks)

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        left = 36
        right = width - 36
        top = 102
        bottom = height - (self.FOOTER_HEIGHT + 50)
        if sidebar_visible:
            left = 24 + 210 + 28
        return {"left": left, "right": right, "top": top, "bottom": bottom}

    def _draw_window_shell(self, canvas, width: int, height: int):
        shadow_round_rect(canvas, 10, 10, width - 10, height - 10, 18, fill=self.theme.panel, outline=self.theme.border, width=2)

    def _draw_title_bar(self, canvas, width: int, callbacks: ChromeCallbacks):
        shadow_round_rect(canvas, 12, 12, width - 12, 80, 16, fill=self.theme.chrome, outline=self.theme.border, width=1)
        canvas.create_line(20, 80, width - 20, 80, fill=self.theme.border, width=1)
        self._draw_menu_icon(canvas, 36, 46, callbacks.toggle_sidebar)
        self._draw_home_icon(canvas, 80, 46, callbacks.home)
        self._draw_window_icon(canvas, width - 92, 46, callbacks.window)
        self._draw_close_icon(canvas, width - 48, 46, callbacks.close)

    def _draw_prompt_strip(self, canvas, width: int, height: int, callbacks: ChromeCallbacks):
        top = height - self.FOOTER_HEIGHT - self.FOOTER_MARGIN
        canvas.create_line(20, top, width - 20, top, fill=self.theme.border, width=1)
        self._draw_status_dot(canvas, 44, height - 54)
        self._draw_prompt_button(canvas, width - 78, height - 58, callbacks.submit_prompt)

    def _draw_status_dot(self, canvas, x: int, y: int):
        return None

    def _draw_menu_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="menu")

    def _draw_home_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="home")

    def _draw_window_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="window")

    def _draw_close_icon(self, canvas, center_x: int, center_y: int, callback):
        self._draw_bar_button(canvas, center_x, center_y, callback, kind="close")

    def _draw_prompt_button(self, canvas, center_x: int, center_y: int, callback):
        tag = "prompt_button"
        button = rounded_rect(
            canvas,
            center_x - 18,
            center_y - 18,
            center_x + 18,
            center_y + 18,
            10,
            fill="",
            outline=self.theme.border,
            width=1,
            tags=(tag,),
        )
        self._prompt_button_item = button
        self._prompt_button_bounds = (center_x - 18, center_y - 18, center_x + 18, center_y + 18)
        self._draw_icon_sprite(
            canvas,
            "Send button icon.png",
            center_x - 2,
            center_y - 6,
            size=32,
            fallback_fill=self.theme.secondary_accent,
            tags=(tag,),
        )
        canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.itemconfigure(button, outline=self.theme.soft_glow))
        canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.itemconfigure(button, outline=self.theme.border))
        canvas.tag_bind(tag, "<Button-1>", lambda _event: callback())
        canvas.tag_raise(tag)
        return button

    def _draw_bar_button(self, canvas, center_x: int, center_y: int, callback, kind: str):
        size = 36
        tag = f"bar_button_{kind}_{center_x}_{center_y}"
        button = rounded_rect(
            canvas,
            center_x - size // 2,
            center_y - size // 2,
            center_x + size // 2,
            center_y + size // 2,
            10,
            fill="",
            outline=self.theme.border,
            width=1,
            tags=(tag,),
        )
        sprite_name = {
            "menu": "Sidebar icon.png",
            "home": "Home icon.png",
            "window": "Inactive Notification icon.png",
            "close": "Close icon.png",
        }[kind]
        self._draw_icon_sprite(canvas, sprite_name, center_x, center_y, size=22, fallback_fill=self.theme.text, tags=(tag,))
        canvas.tag_bind(tag, "<Button-1>", lambda _event: callback())
        canvas.tag_bind(tag, "<Enter>", lambda _event: canvas.itemconfigure(button, outline=self.theme.soft_glow))
        canvas.tag_bind(tag, "<Leave>", lambda _event: canvas.itemconfigure(button, outline=self.theme.border))
        canvas.tag_raise(tag)
        return button

    def _draw_icon_sprite(self, canvas, sprite_name: str, center_x: int, center_y: int, size: int, fallback_fill: str, tags: tuple[str, ...] = ()):
        crop_box = self.sprite_crop_boxes.get(sprite_name)
        sprite = self.sprite_store.get(sprite_name, size, crop_box=crop_box)
        if sprite is not None:
            canvas.create_image(center_x, center_y, image=sprite, anchor="center", tags=tags)
            return
        half = size // 2
        canvas.create_oval(
            center_x - half,
            center_y - half,
            center_x + half,
            center_y + half,
            fill="",
            outline=fallback_fill,
            width=2,
            tags=tags,
        )

    def _focus_prompt_entry(self, _event=None):
        if self.test_entry is not None:
            self.test_entry.focus_set()

    def _sync_test_placeholder(self, *_args):
        if self.test_entry is None or self.test_placeholder is None:
            return

        text = str(self.test_var.get() or "")
        has_text = bool(text.strip())
        if has_text:
            self.test_entry.configure(fg=self.theme.text)
            self.test_placeholder.place_forget()
            return

        self.test_entry.configure(fg=self.theme.text)
        self.test_placeholder.place(x=16, rely=0.5, anchor="w")
        self.test_placeholder.lift()

    def _submit_prompt(self, _event=None):
        self.consume_prompt_text()
        return None

    def consume_prompt_text(self) -> str:
        """Return the current prompt text and reset the footer entry."""

        if self.test_var is None:
            return ""

        text = str(self.test_var.get() or "").strip()
        self.test_value = text
        if self.test_var is not None:
            self.test_var.set("")
        self._sync_test_placeholder()
        return text

    def _on_canvas_motion(self, event):
        self._update_prompt_hover(event.x, event.y)

    def _on_canvas_leave(self, _event):
        self._update_prompt_hover(None, None)

    def _update_prompt_hover(self, x: int | None, y: int | None):
        if self._prompt_button_item is None:
            return

        hovered = self.prompt_button_hovered(x, y)
        return hovered

    def apply_prompt_hover(self, canvas, hovered: bool):
        if self._prompt_button_item is None:
            return
        try:
            canvas.itemconfigure(self._prompt_button_item, outline=self.theme.soft_glow if hovered else self.theme.border)
        except Exception:
            return

    def prompt_button_hovered(self, x: int | None, y: int | None) -> bool:
        x1, y1, x2, y2 = self._prompt_button_bounds
        return x is not None and y is not None and x1 <= x <= x2 and y1 <= y <= y2

    def point_in_title_bar_control(self, x: int, y: int, width: int) -> bool:
        return (
            16 <= x <= 48 and 30 <= y <= 62
        ) or (
            60 <= x <= 96 and 30 <= y <= 62
        ) or (
            width - 108 <= x <= width - 76 and 30 <= y <= 62
        ) or (
            width - 64 <= x <= width - 32 and 30 <= y <= 62
        )

    def layout_prompt_state(self, canvas, x: int | None, y: int | None):
        self.apply_prompt_hover(canvas, self.prompt_button_hovered(x, y))
