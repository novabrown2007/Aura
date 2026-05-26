"""Central manager for provider-neutral LLM access.

Example:
    manager = LLMManager(context)
    response = manager.generateResponse(
        "You are Aura.",
        "Summarize today's schedule.",
    )
    if response.success:
        print(response.text)
"""

from __future__ import annotations

from core.tools.toolOrchestrator import ToolOrchestrator
from modules.llm.models.llmResponse import LLMResponse
from modules.llm.providers.base.llmProvider import LLMProvider
from modules.llm.utils.llmLogger import LLMLogger
from modules.llm.utils.promptBuilder import PromptBuilder


class LLMManager:
    """Single entry point for all LLM access in Aura.

    Providers own vendor-specific request logic. The manager owns provider
    lifecycle, routing, fallback, and offline behavior.
    """

    def __init__(self, context=None):
        """Create a manager with the default provider registry."""

        self.context = context
        self.logger = None
        self.providers: dict[str, LLMProvider] = {}
        self.activeProviderName = "gemini"
        self.fallbackProviderName = "ollama"
        self.offlineMode = False
        self.initialized = False
        self.rawLogger = None

        if context is not None:
            self.initialize(context)

    def initialize(self, context=None):
        """Initialize configured providers and expose the manager on context."""

        if context is not None:
            self.context = context

        config = self.context.config if self.context else None
        self.logger = self._getLogger("LLM.Manager")
        self.rawLogger = LLMLogger(self.context)
        self.activeProviderName = self._getConfigValue(config, "llm.activeProvider", None)
        self.activeProviderName = self.activeProviderName or self._getConfigValue(config, "llm.provider", "gemini")
        self.fallbackProviderName = self._getConfigValue(config, "llm.fallbackProvider", "ollama")

        self.providers = self._createDefaultProviders()

        for provider in self.providers.values():
            provider.initialize()

        self.offlineMode = not bool(self.providers.get("gemini") and self.providers["gemini"].initialized)
        if self.offlineMode:
            self.activeProviderName = self.fallbackProviderName
            if self.logger:
                self.logger.info("Gemini provider unavailable. Using local Ollama in offline mode.")

        if self.context is not None:
            self.context.llmManager = self

        self.initialized = True
        if self.logger:
            self.logger.info(
                f"LLM manager initialized. active={self.activeProviderName}, "
                f"fallback={self.fallbackProviderName}, offline={self.offlineMode}"
            )

    def shutdown(self):
        """Shutdown all initialized providers."""

        for provider in self.providers.values():
            provider.shutdown()
        self.initialized = False

    def setActiveProvider(self, providerName: str) -> bool:
        """Switch the active provider when it exists and is initialized."""

        provider = self.providers.get(providerName)
        if provider is None or not provider.initialized:
            if self.logger:
                self.logger.warning(f"Cannot switch to unavailable LLM provider: {providerName}")
            return False

        self.activeProviderName = providerName
        if self.logger:
            self.logger.info(f"Active LLM provider switched to {providerName}.")
        return True

    def generateResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Generate plain text through the active provider with fallback."""

        return self._routeRequest(
            "generateResponse",
            systemPrompt,
            userPrompt,
            conversationHistory=conversationHistory,
        )

    def generateStructuredResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        schema: dict,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Generate structured JSON through the active provider with fallback."""

        return self._routeRequest(
            "generateStructuredResponse",
            systemPrompt,
            userPrompt,
            schema,
            conversationHistory=conversationHistory,
        )

    def generateToolSelection(
        self,
        systemPrompt: str,
        userPrompt: str,
        toolSchemas: list[dict],
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Parse a user request into deterministic tool-call JSON."""

        toolPrompt = PromptBuilder.buildSystemPrompt(
            systemPrompt,
            toolDefinitions=toolSchemas,
            profile="toolSelection",
        )
        return self.generateStructuredResponse(
            toolPrompt,
            userPrompt,
            ToolOrchestrator.TOOL_CALL_ENVELOPE_SCHEMA,
            conversationHistory=conversationHistory,
        )

    def _routeRequest(
        self,
        methodName: str,
        systemPrompt: str,
        userPrompt: str,
        schema: dict | None = None,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Route one request, falling back when the primary provider fails."""

        providerOrder = self._getProviderOrder()
        lastResponse = LLMResponse(success=False, provider="", error="No LLM provider available.")

        for providerName in providerOrder:
            provider = self.providers.get(providerName)
            if provider is None or not provider.initialized:
                continue

            if self.logger and providerName != self.activeProviderName:
                self.logger.info(f"Routing LLM request to fallback provider: {providerName}")

            method = getattr(provider, methodName)
            if schema is None:
                response = method(systemPrompt, userPrompt, conversationHistory)
            else:
                response = method(systemPrompt, userPrompt, schema, conversationHistory)

            lastResponse = response
            if self.rawLogger:
                self.rawLogger.logExchange(
                    providerName,
                    methodName,
                    systemPrompt,
                    userPrompt,
                    response,
                    schema=schema,
                    conversationHistory=conversationHistory,
                )
            if response.success:
                return response

            if providerName == self.activeProviderName and self._shouldUseOfflineFallback(response.error):
                self.offlineMode = True
                self.activeProviderName = self.fallbackProviderName
                if self.logger:
                    self.logger.warning(f"Gemini became unavailable. Falling back to local Ollama: {response.error}")

            if self.logger:
                self.logger.warning(f"LLM provider '{providerName}' failed: {response.error}")

        return lastResponse

    def getProviderCapabilities(self, providerName: str | None = None):
        """Return provider capability metadata."""

        if providerName is not None:
            provider = self.providers[providerName]
            return provider.getCapabilities().asDict()
        return {
            name: provider.getCapabilities().asDict()
            for name, provider in self.providers.items()
        }

    def _getProviderOrder(self) -> list[str]:
        """Return the active/fallback provider order for the current mode."""

        if self.offlineMode:
            return [self.fallbackProviderName]

        providerOrder = [self.activeProviderName]
        if self.fallbackProviderName not in providerOrder:
            providerOrder.append(self.fallbackProviderName)
        return providerOrder

    def _getLogger(self, name: str):
        """Return a child logger when Aura logging is available."""

        if self.context and getattr(self.context, "logger", None):
            return self.context.logger.getChild(name)
        return None

    def _createDefaultProviders(self) -> dict[str, LLMProvider]:
        """Create default providers lazily so importing LLMManager stays lightweight."""

        from modules.llm.providers.gemini.geminiProvider import GeminiProvider
        from modules.llm.providers.ollama.ollamaProvider import OllamaProvider

        return {
            "gemini": GeminiProvider(self.context),
            "ollama": OllamaProvider(self.context),
        }

    @staticmethod
    def _shouldUseOfflineFallback(error: str | None) -> bool:
        """Return whether a provider failure looks like a reachability issue."""

        if not error:
            return False

        lowered = str(error).lower()
        return any(
            token in lowered
            for token in (
                "not initialized",
                "connection refused",
                "failed to establish",
                "timed out",
                "timeout",
                "temporary failure in name resolution",
                "name or service not known",
                "network",
                "unreachable",
            )
        )

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        """Read config values from Aura's dot-path config interface."""

        if config is None:
            return default
        return config.get(key, default)
