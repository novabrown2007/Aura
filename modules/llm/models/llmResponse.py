"""Provider-neutral LLM response model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.llm.models.toolCall import ToolCall


@dataclass
class LLMResponse:
    """Normalized response returned by every Aura LLM provider."""

    text: str = ""
    success: bool = False
    provider: str = ""
    rawResponse: Any = None
    tokenUsage: dict[str, Any] | None = None
    latency: float | None = None
    toolCalls: list[ToolCall] = field(default_factory=list)
    finishReason: str | None = None
    error: str | None = None

    def asText(self, fallback: str = "") -> str:
        """Return response text, falling back to a caller-provided message."""

        if self.success and self.text.strip():
            return self.text.strip()
        return fallback
