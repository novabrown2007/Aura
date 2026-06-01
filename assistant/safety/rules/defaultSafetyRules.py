"""Default execution safety rules."""

from __future__ import annotations


def buildDefaultSafetyRules() -> list[dict]:
    return [
        {"name": "confirm-high-risk", "description": "High risk actions require confirmation."},
        {"name": "deny-critical-automation", "description": "Critical automation is blocked by default."},
    ]

