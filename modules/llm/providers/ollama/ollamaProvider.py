"""Ollama provider implementation for Aura."""

from __future__ import annotations

import time
from typing import Any

import requests

from modules.llm.models.llmResponse import LLMResponse
from modules.llm.providers.base.llmProvider import LLMProvider
from modules.llm.providers.base.providerCapabilities import ProviderCapabilities
from modules.llm.utils.promptBuilder import PromptBuilder


class OllamaProvider(LLMProvider):
    """Local/offline LLM provider backed by Ollama's generate API."""

    providerName = "ollama"
    capabilities = ProviderCapabilities(
        supportsStructuredOutput=False,
        supportsStreaming=False,
    )

    def initialize(self):
        """Read Ollama configuration and mark the provider available."""

        config = self.context.config if self.context else None
        self.endpoint = self._getConfigValue(config, "llm.providers.ollama.endpoint", None)
        self.endpoint = self.endpoint or self._getConfigValue(config, "llm.ollama.endpoint", None)
        self.endpoint = self.endpoint or self._getConfigValue(config, "llm.endpoint", "http://localhost:11434/api/generate")
        self.endpoint = self._normalizeEndpoint(self.endpoint)
        self.model = self._getConfigValue(config, "llm.providers.ollama.model", None)
        self.model = self.model or self._getConfigValue(config, "llm.ollama.model", None)
        self.model = self.model or self._getConfigValue(config, "llm.model", "llama3.1:8b")
        self.timeout = self._getConfigValue(config, "llm.timeout", 30)
        self.retryCount = self._getConfigValue(config, "llm.retryCount", 1)
        self.logger = self._getLogger("LLM.Ollama")
        self.initialized = True

        if self.logger:
            self.logger.info(f"Ollama provider initialized with model '{self.model}'.")

    def shutdown(self):
        """Ollama does not hold persistent client resources."""

        self.initialized = False

    def generateResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Generate plain text using Ollama."""

        prompt = PromptBuilder.buildPrompt(systemPrompt, userPrompt, conversationHistory)
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        return self._sendGenerateRequest(payload)

    def generateStructuredResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        schema: dict,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Reject trusted structured output requests in offline mode."""

        return LLMResponse(
            provider=self.providerName,
            success=False,
            error="Ollama is configured for offline conversation only and cannot provide trusted structured output.",
        )

    def _sendGenerateRequest(self, payload: dict[str, Any]) -> LLMResponse:
        """Call Ollama and normalize the response."""

        startedAt = time.perf_counter()
        try:
            response = requests.post(self.endpoint, json=payload, timeout=self.timeout)
        except requests.RequestException as error:
            if self.logger:
                self.logger.error(f"Ollama request failed: {error}")
            return LLMResponse(provider=self.providerName, success=False, error=str(error))

        latency = time.perf_counter() - startedAt
        if response.status_code != 200:
            if self.logger:
                self.logger.error(f"Ollama API error: {response.text}")
            return LLMResponse(
                provider=self.providerName,
                success=False,
                rawResponse=response.text,
                latency=latency,
                error=response.text,
            )

        data = response.json()
        text = str(data.get("response") or "").strip()
        if not text:
            return LLMResponse(
                provider=self.providerName,
                success=False,
                rawResponse=data,
                latency=latency,
                error="Ollama response did not include text.",
            )

        return LLMResponse(
            text=text,
            success=True,
            provider=self.providerName,
            rawResponse=data,
            latency=latency,
            finishReason=data.get("done_reason"),
        )

    def _getLogger(self, name: str):
        """Return a child logger when Aura logging is available."""

        if self.context and getattr(self.context, "logger", None):
            return self.context.logger.getChild(name)
        return None

    @staticmethod
    def _normalizeEndpoint(endpoint: str | None) -> str:
        """Normalize Ollama base URLs to the generate API endpoint."""

        endpoint = str(endpoint or "").strip()
        if not endpoint or endpoint == "CHANGE_ME":
            return "http://localhost:11434/api/generate"
        endpoint = endpoint.rstrip("/")
        if endpoint.endswith("/api/generate"):
            return endpoint
        if endpoint.endswith("/api"):
            return f"{endpoint}/generate"
        return f"{endpoint}/api/generate"

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        """Read config values from Aura's dot-path config interface."""

        if config is None:
            return default
        return config.get(key, default)
