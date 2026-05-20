"""Ollama provider implementation for Aura."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from modules.llm.models.llmResponse import LLMResponse
from modules.llm.providers.base.llmProvider import LLMProvider
from modules.llm.utils.promptBuilder import PromptBuilder
from modules.llm.utils.responseValidator import ResponseValidator


class OllamaProvider(LLMProvider):
    """Local/offline LLM provider backed by Ollama's generate API."""

    providerName = "ollama"

    def initialize(self):
        """Read Ollama configuration and mark the provider available."""

        config = self.context.config if self.context else None
        self.endpoint = self._getConfigValue(config, "llm.providers.ollama.endpoint", None)
        self.endpoint = self.endpoint or self._getConfigValue(config, "llm.ollama.endpoint", None)
        self.endpoint = self.endpoint or self._getConfigValue(config, "llm.endpoint", "http://localhost:11434/api/generate")
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
        """Generate JSON with lightweight validation and retry handling."""

        structuredPrompt = self._buildStructuredPrompt(systemPrompt, userPrompt, schema)
        attempts = max(int(self.retryCount), 0) + 1
        lastResponse = LLMResponse(provider=self.providerName, success=False)

        for attempt in range(1, attempts + 1):
            response = self.generateResponse(structuredPrompt, "", conversationHistory)
            lastResponse = response
            if not response.success:
                continue

            valid, parsed, error = ResponseValidator.parseJson(response.text)
            if valid:
                schemaValid, schemaError = ResponseValidator.validateSchema(parsed, schema)
                if schemaValid:
                    response.rawResponse = parsed
                    response.text = json.dumps(parsed)
                    return response
                error = schemaError

            if self.logger:
                self.logger.warning(f"Ollama structured response validation failed on attempt {attempt}: {error}")

        lastResponse.success = False
        lastResponse.error = lastResponse.error or "Ollama returned malformed structured output."
        return lastResponse

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

    @staticmethod
    def _buildStructuredPrompt(systemPrompt: str, userPrompt: str, schema: dict) -> str:
        """Wrap a user prompt with JSON-only structured output instructions."""

        return (
            f"{systemPrompt.strip()}\n\n"
            "Return only valid JSON. Do not include markdown fences or commentary.\n"
            f"Required JSON schema:\n{json.dumps(schema, indent=2)}\n\n"
            f"User request:\n{userPrompt}"
        )

    def _getLogger(self, name: str):
        """Return a child logger when Aura logging is available."""

        if self.context and getattr(self.context, "logger", None):
            return self.context.logger.getChild(name)
        return None

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        """Read config values from Aura's dot-path config interface."""

        if config is None:
            return default
        return config.get(key, default)
