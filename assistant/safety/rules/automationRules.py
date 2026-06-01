"""Automation safety rules."""

from __future__ import annotations


def buildAutomationRules() -> list[dict]:
    return [
        {"name": "no-unsupervised-security-actions"},
        {"name": "no-silent-destructive-actions"},
    ]

