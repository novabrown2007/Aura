"""Chat page for Aura and user conversation."""

from __future__ import annotations

import textwrap

from ..chat_session import ChatSession
from ..drawing import shadow_round_rect
from .base import Page


class ChatPage(Page):
    """Single conversation page with transcript rendering and prompt submission."""

    name = "chat"

    def __init__(self, context=None, post_ui_event=None, thread_factory=None):
        self.session = ChatSession(context=context, post_ui_event=post_ui_event, thread_factory=thread_factory)
        self._transcript_bounds: tuple[int, int, int, int] = (0, 0, 0, 0)

    def set_context(self, context=None, post_ui_event=None):
        self.session.set_context(context=context, post_ui_event=post_ui_event)

    def render(self, canvas, width: int, height: int, theme, sidebar_visible: bool):
        bounds = self.content_bounds(width, height, sidebar_visible)
        left = bounds["left"] + 18
        right = bounds["right"] - 18
        top = bounds["top"] + 12
        bottom = bounds["bottom"] - 18

        canvas.create_text(left, top, anchor="nw", text="Chat", fill=theme.text, font=("Segoe UI", 18, "bold"))
        canvas.create_text(left, top + 28, anchor="nw", text="Session history", fill=theme.placeholder, font=("Segoe UI", 10))

        transcript_left = left
        transcript_right = right
        transcript_top = top + 60
        transcript_bottom = bottom
        self._draw_transcript(canvas, theme, transcript_left, transcript_top, transcript_right, transcript_bottom)

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        left = 36
        right = width - 36
        top = 102
        bottom = height - 148
        if sidebar_visible:
            left = 24 + 210 + 28
        return {"left": left, "right": right, "top": top, "bottom": bottom}

    def handle_press(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        return self._point_in_bounds(x, y, self._transcript_bounds)

    def handle_scroll(self, delta: int, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if not self._point_in_bounds(x, y, self._transcript_bounds):
            return False
        return self.session.scroll(delta, max(1, self._transcript_bounds[3] - self._transcript_bounds[1]))

    def submit_prompt(self, prompt: str) -> bool:
        return self.session.submit(prompt)

    def _draw_transcript(self, canvas, theme, left: int, top: int, right: int, bottom: int):
        self._transcript_bounds = (left, top, right, bottom)
        shadow_round_rect(
            canvas,
            left,
            top,
            right,
            bottom,
            18,
            fill=theme.tertiary_background,
            outline=theme.border,
            width=2,
        )

        canvas.create_text(left + 24, top + 18, anchor="nw", text="Conversation", fill=theme.text, font=("Segoe UI", 12, "bold"))
        canvas.create_text(left + 24, top + 40, anchor="nw", text="Scroll to review older messages", fill=theme.placeholder, font=("Segoe UI", 9))

        viewport_left = left + 18
        viewport_top = top + 64
        viewport_right = right - 22
        viewport_bottom = bottom - 20
        viewport_height = max(1, viewport_bottom - viewport_top)

        layout = self._layout_messages(self.session.messages, viewport_right - viewport_left)
        total_height = sum(item["height"] for item in layout) + max(0, len(layout) - 1) * 14
        max_scroll = max(0, total_height - viewport_height)
        self.session.max_scroll = max_scroll
        self.session.scroll_offset = max(0, min(int(self.session.scroll_offset or 0), max_scroll))

        if not layout:
            canvas.create_text(
                viewport_left + 6,
                viewport_top + 24,
                anchor="nw",
                text="Use the footer input to start chatting with Aura.",
                fill=theme.placeholder,
                font=("Segoe UI", 11),
            )
            return

        cursor = viewport_bottom + self.session.scroll_offset
        rendered = []
        for item in reversed(layout):
            bubble_height = item["height"]
            bubble_top = cursor - bubble_height
            bubble_bottom = cursor
            cursor = bubble_top - 14
            if bubble_bottom < viewport_top:
                break
            if bubble_top > viewport_bottom:
                continue
            rendered.append((bubble_top, item))

        for bubble_top, item in reversed(rendered):
            message = item["message"]
            wrapped = item["wrapped"]
            bubble_width = item["bubble_width"]
            bubble_height = item["height"]
            is_user = message.role == "user"
            bubble_x1 = viewport_right - bubble_width if is_user else viewport_left
            bubble_x2 = viewport_right if is_user else viewport_left + bubble_width
            fill = theme.secondary_accent if is_user else theme.panel
            outline = theme.soft_glow if is_user else theme.border
            text_fill = theme.background if is_user else theme.text
            shadow_round_rect(
                canvas,
                bubble_x1,
                bubble_top,
                bubble_x2,
                bubble_top + bubble_height,
                16,
                fill=fill,
                outline=outline,
                width=2,
            )
            canvas.create_text(
                bubble_x1 + 18,
                bubble_top + 14,
                anchor="nw",
                text="\n".join(wrapped),
                fill=text_fill,
                font=("Segoe UI", 11),
                width=bubble_width - 36,
                justify="left",
            )
            if message.state == "pending":
                canvas.create_text(
                    bubble_x2 - 18,
                    bubble_top + bubble_height - 12,
                    anchor="se",
                    text="Thinking...",
                    fill=theme.placeholder,
                    font=("Segoe UI", 9, "italic"),
                )
            elif message.state == "error":
                canvas.create_text(
                    bubble_x2 - 18,
                    bubble_top + bubble_height - 12,
                    anchor="se",
                    text="Error",
                    fill=theme.placeholder,
                    font=("Segoe UI", 9, "italic"),
                )

        self._draw_scrollbar(canvas, theme, viewport_right, viewport_top, viewport_bottom, self.session.scroll_offset, max_scroll)

    def _layout_messages(self, messages, available_width: int) -> list[dict]:
        width = max(320, available_width)
        bubble_padding_x = 18
        bubble_padding_y = 14
        max_text_width = max(220, int(width * 0.68))
        layout = []
        for message in messages:
            text = str(message.text or "").strip()
            if not text:
                continue
            wrapped = self._wrap_text(text, max_text_width)
            line_count = max(1, len(wrapped))
            text_height = 19 * line_count
            bubble_width = min(max_text_width + bubble_padding_x * 2, width)
            bubble_height = text_height + bubble_padding_y * 2
            layout.append(
                {
                    "message": message,
                    "wrapped": wrapped,
                    "bubble_width": bubble_width,
                    "height": bubble_height,
                }
            )
        return layout

    def _draw_scrollbar(self, canvas, theme, track_x: int, top: int, bottom: int, scroll_offset: int, max_scroll: int):
        track_left = track_x - 10
        track_right = track_x - 5
        shadow_round_rect(
            canvas,
            track_left,
            top,
            track_right,
            bottom,
            4,
            fill=theme.shadow,
            outline=theme.shadow,
            width=1,
        )
        if max_scroll <= 0:
            return
        track_height = max(1, bottom - top)
        thumb_height = max(48, int((track_height * track_height) / max(1, track_height + max_scroll)))
        thumb_height = min(track_height, thumb_height)
        thumb_range = max(1, track_height - thumb_height)
        thumb_top = top + int((scroll_offset / max_scroll) * thumb_range)
        shadow_round_rect(
            canvas,
            track_left,
            thumb_top,
            track_right,
            thumb_top + thumb_height,
            4,
            fill=theme.border,
            outline=theme.soft_glow,
            width=1,
        )

    @staticmethod
    def _wrap_text(text: str, max_width: int) -> list[str]:
        average_char_width = 7.2
        max_chars = max(24, int(max_width / average_char_width))
        lines: list[str] = []
        for paragraph in str(text or "").splitlines() or [""]:
            wrapped = textwrap.wrap(
                paragraph,
                width=max_chars,
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines.extend(wrapped or [""])
        return lines

    @staticmethod
    def _point_in_bounds(x: int, y: int, bounds: tuple[int, int, int, int]) -> bool:
        x1, y1, x2, y2 = bounds
        return x1 <= x <= x2 and y1 <= y <= y2

