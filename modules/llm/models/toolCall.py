"""Structured representation of an LLM-requested tool call."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """Provider-neutral tool call metadata.

    LLM providers should only describe the requested tool call. Execution is
    intentionally owned by deterministic Aura systems outside the LLM layer.
    """

    toolName: str
    arguments: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

