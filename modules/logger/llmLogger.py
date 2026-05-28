"""Dedicated LLM conversation trace logging for Aura."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from modules.logger.logManager import LogManager


class LLMLogger:
    """
    Isolated logger for raw LLM prompts, provider responses, and parse errors.

    LLM traces are intentionally separated from normal runtime logs because
    prompts and responses are large and high-signal only during model debugging.
    """

    def __init__(self, context=None, logManager: LogManager | None = None):
        """Configure the LLM logger from runtime config or a supplied manager."""

        self.context = context
        config = getattr(context, "config", None) if context else None
        if logManager is not None:
            self.logManager = logManager
        elif context is not None and getattr(context, "logger", None):
            self.logManager = context.logger.logManager
        else:
            self.logManager = LogManager.fromConfig(config)

        self.enabled = bool(self._getConfigValue(config, "llm.logging.enabled", True))

    def logPrompt(
        self,
        provider: str = "",
        systemPrompt: str = "",
        memoryContext: str = "",
        userMessage: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        """Log a prompt before it is sent to a provider."""

        self._writeInteraction(
            provider=provider,
            systemPrompt=systemPrompt,
            memoryContext=memoryContext,
            userMessage=userMessage,
            metadata=metadata,
        )

    def logResponse(
        self,
        provider: str = "",
        rawResponse: Any = "",
        latency: float | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Log a provider response."""

        self._writeInteraction(
            provider=provider,
            rawResponse=self._stringify(rawResponse),
            latency=latency,
            metadata=metadata,
        )

    def logError(
        self,
        provider: str = "",
        error: Any = "",
        systemPrompt: str = "",
        userMessage: str = "",
        rawResponse: Any = "",
        latency: float | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Log a provider or parsing error."""

        self._writeInteraction(
            provider=provider,
            systemPrompt=systemPrompt,
            userMessage=userMessage,
            rawResponse=self._stringify(rawResponse),
            latency=latency,
            error=self._stringify(error),
            metadata=metadata,
        )

    def logInteraction(
        self,
        provider: str = "",
        systemPrompt: str = "",
        memoryContext: str = "",
        userMessage: str = "",
        rawResponse: Any = "",
        latency: float | None = None,
        metadata: dict[str, Any] | None = None,
        error: Any = None,
    ):
        """Log a complete LLM interaction in the dedicated trace stream."""

        self._writeInteraction(
            provider=provider,
            systemPrompt=systemPrompt,
            memoryContext=memoryContext,
            userMessage=userMessage,
            rawResponse=self._stringify(rawResponse),
            latency=latency,
            metadata=metadata,
            error=self._stringify(error) if error is not None else "",
        )

    def logExchange(
        self,
        provider: str,
        methodName: str,
        systemPrompt: str,
        userPrompt: str,
        response,
        schema: dict[str, Any] | None = None,
        conversationHistory: list | None = None,
    ):
        """Compatibility helper used by the provider-neutral LLM manager."""

        metadata = {
            "method": methodName,
            "schema": schema,
            "conversationHistory": conversationHistory or [],
            "success": getattr(response, "success", False),
            "tokenUsage": getattr(response, "tokenUsage", None),
            "finishReason": getattr(response, "finishReason", None),
        }
        self.logInteraction(
            provider=provider,
            systemPrompt=systemPrompt,
            userMessage=userPrompt,
            rawResponse=getattr(response, "text", "") or getattr(response, "rawResponse", ""),
            latency=getattr(response, "latency", None),
            metadata=metadata,
            error=getattr(response, "error", None),
        )

    def logPipelineStage(self, stage: str, message: str):
        """Log a cognition pipeline stage without writing to console."""

        self._writeInteraction(
            provider="pipeline",
            metadata={"stage": stage},
            rawResponse=message,
        )

    def _writeInteraction(
        self,
        provider: str = "",
        systemPrompt: str = "",
        memoryContext: str = "",
        userMessage: str = "",
        rawResponse: str = "",
        latency: float | None = None,
        metadata: dict[str, Any] | None = None,
        error: str = "",
    ):
        """Format and append one isolated LLM trace block."""

        if not self.enabled:
            return

        lines = [
            "==============================",
            f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"PROVIDER: {provider}",
            "",
            "SYSTEM PROMPT:",
            systemPrompt or "",
            "",
            "MEMORY CONTEXT:",
            memoryContext or "",
            "",
            "USER MESSAGE:",
            userMessage or "",
            "",
            "RAW RESPONSE:",
            rawResponse or "",
            "",
            "LATENCY:",
            "" if latency is None else f"{float(latency):.2f}s",
        ]
        if error:
            lines.extend(["", "ERROR:", error])
        if metadata:
            lines.extend(["", "METADATA:", json.dumps(metadata, indent=2, default=str)])
        lines.append("==============================")
        self.logManager.appendLlmEntry("\n".join(lines))

    @staticmethod
    def _stringify(value: Any) -> str:
        """Safely convert provider payloads to readable text."""

        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, indent=2, default=str)
        except Exception:
            return str(value)

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        """Read config values from Aura config objects."""

        if config is None:
            return default
        return config.get(key, default)

