"""Google Gemini provider implementation for Aura."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from modules.llm.models.llmResponse import LLMResponse
from modules.llm.providers.base.llmProvider import LLMProvider
from modules.llm.providers.base.providerCapabilities import ProviderCapabilities
from modules.llm.utils.promptBuilder import PromptBuilder
from modules.llm.utils.responseValidator import ResponseValidator


class GeminiProvider(LLMProvider):
    """Gemini provider using Google's official SDK when installed."""

    providerName = "gemini"
    capabilities = ProviderCapabilities(
        supportsStructuredOutput=True,
        supportsStreaming=True,
        supportsVision=True,
        supportsFileSearch=True,
        supportsUrlContext=True,
        supportsToolCalling=False,
    )

    def initialize(self):
        """Initialize the Gemini client from config or environment."""

        config = self.context.config if self.context else None
        self.logger = self._getLogger("LLM.Gemini")
        self.apiKey = self._getConfigValue(config, "llm.providers.gemini.apiKey", None)
        self.apiKey = self.apiKey or self._getConfigValue(config, "llm.providers.gemini.api_secret", None)
        self.apiKey = self.apiKey or self._getConfigValue(config, "llm.gemini.apiKey", None)
        self.apiKey = self.apiKey or self._getConfigValue(config, "llm.gemini.api_secret", None)
        self.apiKey = self.apiKey or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = self._getConfigValue(config, "llm.providers.gemini.model", "gemini-2.5-flash")
        self.model = self._getConfigValue(config, "llm.gemini.model", self.model)
        self.timeout = self._getConfigValue(config, "llm.timeout", 30)
        self.retryCount = self._getConfigValue(config, "llm.retryCount", 2)
        self.client = None

        if not self.apiKey:
            self.initialized = False
            if self.logger:
                self.logger.warning("Gemini provider disabled because no API key was configured.")
            return

        try:
            from google import genai
        except ImportError as error:
            self.initialized = False
            if self.logger:
                self.logger.error(f"Gemini SDK is not installed: {error}")
            return

        self.client = genai.Client(api_key=self.apiKey)
        self.initialized = True
        if self.logger:
            self.logger.info(f"Gemini provider initialized with model '{self.model}'.")

    def shutdown(self):
        """Release Gemini client reference."""

        self.client = None
        self.initialized = False

    def generateResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Generate normal text using Gemini."""

        prompt = PromptBuilder.buildPrompt(systemPrompt, userPrompt, conversationHistory)
        return self._callGemini(prompt)

    def generateStructuredResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        schema: dict,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Generate validated JSON using Gemini with malformed-output retries."""

        prompt = self._buildStructuredPrompt(systemPrompt, userPrompt, schema)
        attempts = max(int(self.retryCount), 0) + 1
        lastResponse = LLMResponse(provider=self.providerName, success=False)

        for attempt in range(1, attempts + 1):
            finalPrompt = PromptBuilder.buildPrompt(prompt, "", conversationHistory)
            response = self._callGemini(finalPrompt, forceJson=True, jsonSchema=schema)
            lastResponse = response
            if not response.success:
                if self.logger:
                    self.logger.warning(f"Gemini structured request failed on attempt {attempt}: {response.error}")
                continue

            valid, parsed, error = ResponseValidator.parseJson(response.text)
            if not valid:
                repairedText = ResponseValidator.repairJsonText(response.text)
                valid, parsed, error = ResponseValidator.parseJson(repairedText)
            if valid:
                schemaValid, schemaError = ResponseValidator.validateSchema(parsed, schema)
                if schemaValid:
                    response.rawResponse = parsed
                    response.text = json.dumps(parsed)
                    return response
                error = schemaError

            if self.logger:
                self.logger.warning(f"Gemini structured response validation failed on attempt {attempt}: {error}")

        lastResponse.success = False
        lastResponse.error = lastResponse.error or "Gemini returned malformed structured output."
        return lastResponse

    def _callGemini(
        self,
        prompt: str,
        forceJson: bool = False,
        jsonSchema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Call Gemini and normalize the SDK response."""

        if not self.initialized or self.client is None:
            return LLMResponse(
                provider=self.providerName,
                success=False,
                error="Gemini provider is not initialized.",
            )

        startedAt = time.perf_counter()
        try:
            config = None
            if forceJson:
                config = {"response_mime_type": "application/json"}
                if jsonSchema is not None:
                    config["response_json_schema"] = jsonSchema
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as error:
            if self.logger:
                self.logger.error(f"Gemini request failed: {error}")
            return LLMResponse(provider=self.providerName, success=False, error=str(error))

        latency = time.perf_counter() - startedAt
        text = str(getattr(response, "text", "") or "").strip()
        if not text:
            return LLMResponse(
                provider=self.providerName,
                success=False,
                rawResponse=response,
                latency=latency,
                error="Gemini response did not include text.",
            )

        return LLMResponse(
            text=text,
            success=True,
            provider=self.providerName,
            rawResponse=response,
            latency=latency,
            finishReason=self._extractFinishReason(response),
        )

    @staticmethod
    def _buildStructuredPrompt(systemPrompt: str, userPrompt: str, schema: dict) -> str:
        """Build JSON-only instructions for Gemini structured mode."""

        return (
            f"{systemPrompt.strip()}\n\n"
            "Return only valid JSON matching this schema. No markdown. No commentary.\n"
            f"Schema:\n{json.dumps(schema, indent=2)}\n\n"
            f"User request:\n{userPrompt}"
        )

    @staticmethod
    def _extractFinishReason(response: Any) -> str | None:
        """Best-effort finish reason extraction across SDK response shapes."""

        candidates = getattr(response, "candidates", None)
        if candidates:
            firstCandidate = candidates[0]
            return getattr(firstCandidate, "finish_reason", None)
        return None

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
