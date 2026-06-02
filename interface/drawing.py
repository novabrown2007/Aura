"""Small drawing helpers used by the Aura window components."""

from __future__ import annotations


def rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=36, **kwargs)


def shadow_round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    shadow_offset = 3
    shadow_points = [
        x1 + radius + shadow_offset,
        y1 + shadow_offset,
        x2 - radius + shadow_offset,
        y1 + shadow_offset,
        x2 + shadow_offset,
        y1 + shadow_offset,
        x2 + shadow_offset,
        y1 + radius + shadow_offset,
        x2 + shadow_offset,
        y2 - radius + shadow_offset,
        x2 + shadow_offset,
        y2 + shadow_offset,
        x2 - radius + shadow_offset,
        y2 + shadow_offset,
        x1 + radius + shadow_offset,
        y2 + shadow_offset,
        x1 + shadow_offset,
        y2 + shadow_offset,
        x1 + shadow_offset,
        y2 - radius + shadow_offset,
        x1 + shadow_offset,
        y1 + radius + shadow_offset,
        x1 + shadow_offset,
        y1 + shadow_offset,
    ]
    canvas.create_polygon(
        shadow_points,
        smooth=True,
        splinesteps=36,
        fill="#0B1014",
        outline="#0B1014",
    )
    return rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs)
