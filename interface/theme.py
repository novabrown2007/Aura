"""Shared visual theme for Aura window components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    background: str = "#0f141c"
    panel: str = "#171f2b"
    tertiary_background: str = "#00112b"
    border: str = "#344A55"
    chrome: str = "#171f2b"
    text: str = "#e8eef7"
    placeholder: str = "#AAB6C3"
    accent: str = "#9D4EDD"
    secondary_accent: str = "#C77DFF"
    soft_glow: str = "#7B2CBF"
    shadow: str = "#0B1014"
