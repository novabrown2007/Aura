"""Module permission rules."""

from __future__ import annotations


def buildModulePermissionRules() -> list[dict]:
    return [
        {"permission": "system:lifecycle", "module": "system"},
        {"permission": "calendar.write", "module": "calendar"},
        {"permission": "smartHome.security", "module": "homeAutomation"},
    ]

