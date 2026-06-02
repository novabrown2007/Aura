"""Default home page for the Aura middle content area."""

from __future__ import annotations

from dataclasses import dataclass

from ..theme import Theme
from .base import Page


@dataclass(frozen=True)
class TileSpec:
    tile_id: int
    title: str


class HomePage(Page):
    """The current dashboard-style middle page."""

    name = "home"

    def __init__(self):
        self._active_tile_id: int | None = None
        self._active_tile_offset = (0, 0)
        self._drag_position: tuple[int, int] | None = None
        self._tile_order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        self._tile_specs = [
            TileSpec(0, "Widget 1"),
            TileSpec(1, "Widget 2"),
            TileSpec(2, "Widget 3"),
            TileSpec(3, "Widget 4"),
            TileSpec(4, "Widget 5"),
            TileSpec(5, "Widget 6"),
            TileSpec(6, "Widget 7"),
            TileSpec(7, "Widget 8"),
            TileSpec(8, "Widget 9"),
            TileSpec(9, "Widget 10"),
            TileSpec(10, "Widget 11"),
            TileSpec(11, "Widget 12"),
        ]
        self._tile_size = (320, 180)
        self._tile_columns = 4
        self._tile_rows = 3
        self._tile_gap = (18, 18)

    def render(self, canvas, width: int, height: int, theme: Theme, sidebar_visible: bool):
        bounds = self.content_bounds(width, height, sidebar_visible)
        tile_size = self.tile_dimensions(bounds)
        tile_positions = self.tile_positions(bounds["left"], bounds["top"], bounds["right"], bounds["bottom"], tile_size, sidebar_visible)

        for slot_index, (x, y) in enumerate(tile_positions):
            tile_id = self._tile_order[slot_index]
            spec = self._tile_specs[tile_id]
            if self._active_tile_id == tile_id and self._drag_position is not None:
                draw_x, draw_y = self._drag_position
                active = True
            else:
                draw_x, draw_y = x, y
                active = False
            self._draw_tile(canvas, draw_x, draw_y, spec.title, tile_size, theme, active=active)

    def handle_press(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        tile_id = self.hit_test_tile(x, y, width, height, sidebar_visible)
        if tile_id is None:
            return False

        slot_index = self.slot_index_for_tile(tile_id)
        bounds = self.content_bounds(width, height, sidebar_visible)
        tile_size = self.tile_dimensions(bounds)
        tile_x, tile_y = self.tile_positions(bounds["left"], bounds["top"], bounds["right"], bounds["bottom"], tile_size, sidebar_visible)[slot_index]
        self._active_tile_id = tile_id
        self._active_tile_offset = (x - tile_x, y - tile_y)
        self._drag_position = (tile_x, tile_y)
        return True

    def handle_drag(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self._active_tile_id is None:
            return False
        offset_x, offset_y = self._active_tile_offset
        self._drag_position = (x - offset_x, y - offset_y)
        return True

    def handle_release(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> bool:
        if self._active_tile_id is None:
            return False

        tile_x, tile_y = self._drag_position or (0, 0)
        bounds = self.content_bounds(width, height, sidebar_visible)
        tile_w, tile_h = self.tile_dimensions(bounds)
        center_x = tile_x + tile_w / 2
        center_y = tile_y + tile_h / 2
        target_slot = self.nearest_slot(center_x, center_y, bounds, (tile_w, tile_h), sidebar_visible)
        current_slot = self.slot_index_for_tile(self._active_tile_id)

        if target_slot != current_slot:
            tile_id = self._tile_order.pop(current_slot)
            self._tile_order.insert(target_slot, tile_id)

        self._active_tile_id = None
        self._drag_position = None
        return True

    def content_bounds(self, width: int, height: int, sidebar_visible: bool) -> dict[str, int]:
        left = 36
        right = width - 36
        top = 102
        bottom = height - 138
        if sidebar_visible:
            left = 24 + 210 + 28
        return {"left": left, "right": right, "top": top, "bottom": bottom}

    def tile_dimensions(self, bounds: dict[str, int]) -> tuple[int, int]:
        tile_w_max, tile_h_max = self._tile_size
        avail_w = max(0, bounds["right"] - bounds["left"])
        avail_h = max(0, bounds["bottom"] - bounds["top"])
        gap_x, gap_y = self._tile_gap
        tile_w = min(tile_w_max, max(120, (avail_w - gap_x * (self._tile_columns - 1)) // self._tile_columns))
        tile_h = min(tile_h_max, max(100, (avail_h - gap_y * (self._tile_rows - 1)) // self._tile_rows))
        return int(tile_w), int(tile_h)

    def tile_positions(self, left: int, top: int, right: int, bottom: int, tile_size: tuple[int, int], sidebar_visible: bool) -> list[tuple[int, int]]:
        tile_w, tile_h = tile_size
        gap_x, gap_y = self._tile_gap
        avail_w = max(tile_w, right - left)
        avail_h = max(tile_h, bottom - top)
        grid_w = tile_w * self._tile_columns + gap_x * (self._tile_columns - 1)
        grid_h = tile_h * self._tile_rows + gap_y * (self._tile_rows - 1)
        start_x = left + max(0, (avail_w - grid_w) // 2)
        start_y = top + max(0, (avail_h - grid_h) // 2)
        if sidebar_visible:
            start_x = left
        positions = []
        for row in range(self._tile_rows):
            for col in range(self._tile_columns):
                positions.append((start_x + col * (tile_w + gap_x), start_y + row * (tile_h + gap_y)))
        return positions

    def hit_test_tile(self, x: int, y: int, width: int, height: int, sidebar_visible: bool) -> int | None:
        bounds = self.content_bounds(width, height, sidebar_visible)
        tile_size = self.tile_dimensions(bounds)
        positions = self.tile_positions(bounds["left"], bounds["top"], bounds["right"], bounds["bottom"], tile_size, sidebar_visible)
        for slot_index, (tile_x, tile_y) in enumerate(positions):
            tile_id = self._tile_order[slot_index]
            if tile_x <= x <= tile_x + tile_size[0] and tile_y <= y <= tile_y + tile_size[1]:
                return tile_id
        return None

    def slot_index_for_tile(self, tile_id: int) -> int:
        for index, current in enumerate(self._tile_order):
            if current == tile_id:
                return index
        return 0

    def nearest_slot(self, center_x: float, center_y: float, bounds: dict[str, int], tile_size: tuple[int, int], sidebar_visible: bool) -> int:
        positions = self.tile_positions(bounds["left"], bounds["top"], bounds["right"], bounds["bottom"], tile_size, sidebar_visible)
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
    def _draw_tile(canvas, x: int, y: int, title: str, tile_size: tuple[int, int], theme: Theme, active: bool = False):
        width, height = tile_size
        fill = theme.tertiary_background if not active else theme.secondary_accent
        outline = theme.secondary_accent if active else theme.border
        from ..drawing import shadow_round_rect

        shadow_round_rect(canvas, x, y, x + width, y + height, 16, fill=fill, outline=outline, width=2)
        canvas.create_text(x + 20, y + 20, anchor="nw", text=title, fill=theme.placeholder, font=("Segoe UI", 10))
