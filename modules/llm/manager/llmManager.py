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

import re
import time
from threading import Lock
from uuid import uuid4

from core.tools.toolOrchestrator import ToolOrchestrator
from modules.llm.models.llmResponse import LLMResponse
from modules.llm.providers.base.llmProvider import LLMProvider
from modules.llm.utils.promptBuilder import PromptBuilder
from modules.logger.llmLogger import LLMLogger


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
        self.activeProviderName = "ollama"
        self.preferredProviderName = "ollama"
        self.fallbackProviderName = ""
        self.offlineMode = False
        self.offlineReason = ""
        self.offlineUntil = 0.0
        self.initialized = False
        self.rawLogger = None
        self._activeRequestIds: set[str] = set()
        self._requestLock = Lock()

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
        self.activeProviderName = self.activeProviderName or self._getConfigValue(config, "llm.provider", "ollama")
        self.preferredProviderName = self.activeProviderName
        self.fallbackProviderName = self._normalizeProviderName(
            self._getConfigValue(config, "llm.fallbackProvider", "")
        )

        self.providers = self._createDefaultProviders()

        for provider in self.providers.values():
            provider.initialize()

        preferredProvider = self.providers.get(self.preferredProviderName)
        self.offlineMode = not bool(preferredProvider and preferredProvider.initialized)
        if self.offlineMode:
            self.offlineReason = "Preferred LLM provider unavailable at startup."
            if self._hasFallbackProvider():
                self.activeProviderName = self.fallbackProviderName
            else:
                self.activeProviderName = self.preferredProviderName
            if self.logger:
                if self._hasFallbackProvider():
                    self.logger.info(
                        f"Preferred LLM provider unavailable. Using {self.fallbackProviderName} in offline mode."
                    )
                else:
                    self.logger.info("Preferred LLM provider unavailable. No conversational fallback provider configured.")

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
        self.preferredProviderName = providerName
        self.offlineMode = False
        self.offlineReason = ""
        self.offlineUntil = 0.0
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

            if not self._providerSupportsRequest(provider, methodName):
                if self.logger:
                    self.logger.info(f"Skipping LLM provider '{providerName}' for unsupported request: {methodName}")
                if not lastResponse.error or lastResponse.error == "No LLM provider available.":
                    lastResponse = LLMResponse(
                        success=False,
                        provider=providerName,
                        error=f"Provider '{providerName}' does not support {methodName}.",
                    )
                continue

            if self.logger and providerName != self.activeProviderName:
                if providerName == self.preferredProviderName:
                    self.logger.info(f"Retrying preferred LLM provider: {providerName}")
                else:
                    self.logger.info(f"Routing LLM request to fallback provider: {providerName}")

            method = getattr(provider, methodName)
            operationId, token = self._beginProviderRequest(providerName, methodName)
            try:
                if token is not None and token.cancellationRequested:
                    return LLMResponse(success=False, provider=providerName, error="Provider request cancelled.")
                if schema is None:
                    response = method(systemPrompt, userPrompt, conversationHistory)
                else:
                    response = method(systemPrompt, userPrompt, schema, conversationHistory)
                if token is not None and token.cancellationRequested:
                    return LLMResponse(success=False, provider=providerName, error="Provider request cancelled.")
            finally:
                self._finishProviderRequest(operationId)

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
                if providerName == self.preferredProviderName:
                    self._restorePreferredProvider()
                return response

            if providerName == self.preferredProviderName and self._shouldUseOfflineFallback(response.error):
                self._enterOfflineFallback(response.error)

            if self.logger:
                self.logger.warning(f"LLM provider '{providerName}' failed: {response.error}")

        return lastResponse

    def cancelActiveRequests(self) -> list[str]:
        """Request cooperative cancellation for active provider requests."""

        with self._requestLock:
            requestIds = list(self._activeRequestIds)

        cancellationManager = getattr(self.context, "cancellationManager", None)
        for operationId in requestIds:
            try:
                if cancellationManager is not None:
                    cancellationManager.cancel(operationId)
            except Exception:
                pass

        for provider in getattr(self, "providers", {}).values():
            if hasattr(provider, "cancelActiveRequests"):
                try:
                    provider.cancelActiveRequests()
                except Exception as error:
                    if self.logger:
                        self.logger.warning(f"Provider cancellation hook failed: {error}")
        return requestIds

    def _beginProviderRequest(self, providerName: str, methodName: str):
        """Register a provider request as an interruptible operation."""

        operationId = f"provider.{providerName}.{methodName}.{uuid4().hex}"
        token = None
        cancellationManager = getattr(self.context, "cancellationManager", None)
        registry = getattr(self.context, "interruptionRegistry", None)
        try:
            if cancellationManager is not None:
                token = cancellationManager.createToken(operationId)
            if registry is not None:
                registry.registerOperation(
                    operationId,
                    "provider",
                    "provider",
                    cancelHandler=lambda _context: self.cancelActiveRequests(),
                    metadata={"provider": providerName, "method": methodName},
                )
            with self._requestLock:
                self._activeRequestIds.add(operationId)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Failed to register provider interruption operation: {error}")
        return operationId, token

    def _finishProviderRequest(self, operationId: str):
        """Remove provider request interruption metadata."""

        with self._requestLock:
            self._activeRequestIds.discard(operationId)
        registry = getattr(self.context, "interruptionRegistry", None)
        if registry is not None:
            try:
                registry.completeOperation(operationId)
            except Exception:
                pass
        cancellationManager = getattr(self.context, "cancellationManager", None)
        if cancellationManager is not None and hasattr(cancellationManager, "complete"):
            cancellationManager.complete(operationId)

    @staticmethod
    def _providerSupportsRequest(provider: LLMProvider, methodName: str) -> bool:
        """Return whether a provider should receive this kind of request."""

        if methodName != "generateStructuredResponse":
            return True
        try:
            capabilities = provider.getCapabilities()
        except Exception:
            capabilities = getattr(provider, "capabilities", None)
        if capabilities is None:
            return True
        return bool(getattr(capabilities, "supportsStructuredOutput", True))

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
            if self._fallbackCooldownExpired():
                providerOrder = [self.preferredProviderName]
                if self._hasFallbackProvider():
                    providerOrder.append(self.fallbackProviderName)
                return providerOrder
            return [self.fallbackProviderName] if self._hasFallbackProvider() else []

        providerOrder = [self.activeProviderName]
        if self._hasFallbackProvider() and self.fallbackProviderName not in providerOrder:
            providerOrder.append(self.fallbackProviderName)
        return providerOrder

    def canUseStructuredOutput(self) -> bool:
        """Return whether structured/tool parsing can be attempted now."""

        if not self.offlineMode:
            return True
        if self._fallbackCooldownExpired():
            return True
        fallbackProvider = self.providers.get(self.fallbackProviderName)
        if fallbackProvider is None or not fallbackProvider.initialized:
            return False
        return self._providerSupportsRequest(fallbackProvider, "generateStructuredResponse")

    def getStatus(self) -> dict:
        """Return concise provider routing state for interfaces and diagnostics."""

        activeProvider = self.providers.get(self.activeProviderName)
        preferredProvider = self.providers.get(self.preferredProviderName)
        fallbackProvider = self.providers.get(self.fallbackProviderName)
        return {
            "activeProvider": self.activeProviderName,
            "preferredProvider": self.preferredProviderName,
            "fallbackProvider": self.fallbackProviderName,
            "activeModel": str(getattr(activeProvider, "model", "") or self.activeProviderName),
            "preferredModel": str(getattr(preferredProvider, "model", "") or self.preferredProviderName),
            "fallbackModel": str(getattr(fallbackProvider, "model", "") or self.fallbackProviderName),
            "offlineMode": self.offlineMode,
            "offlineReason": self.offlineReason,
            "offlineUntil": self.offlineUntil,
            "canUseStructuredOutput": self.canUseStructuredOutput(),
        }

    def _enterOfflineFallback(self, error: str | None):
        """Switch routing to fallback temporarily after primary provider failure."""

        self.offlineMode = True
        self.offlineReason = str(error or "Primary provider unavailable.")
        self.offlineUntil = time.time() + self._fallbackRetryDelay(error)
        if self._hasFallbackProvider():
            self.activeProviderName = self.fallbackProviderName
        else:
            self.activeProviderName = self.preferredProviderName
        if self.logger:
            if self._hasFallbackProvider():
                self.logger.warning(
                    f"Preferred LLM provider became unavailable. Falling back to {self.fallbackProviderName}: {error}"
                )
            else:
                self.logger.warning(
                    f"Preferred LLM provider became unavailable. No conversational fallback configured: {error}"
                )

    def _restorePreferredProvider(self):
        """Mark the preferred provider as active after a successful retry."""

        if self.activeProviderName != self.preferredProviderName or self.offlineMode:
            if self.logger:
                self.logger.info(f"Preferred LLM provider restored: {self.preferredProviderName}")
        self.activeProviderName = self.preferredProviderName
        self.offlineMode = False
        self.offlineReason = ""
        self.offlineUntil = 0.0

    def _fallbackCooldownExpired(self) -> bool:
        """Return whether it is time to retry the preferred provider."""

        return time.time() >= float(self.offlineUntil or 0.0)

    def _hasFallbackProvider(self) -> bool:
        """Return whether routing may use a configured fallback provider."""

        return bool(self.fallbackProviderName and self.fallbackProviderName in self.providers)

    @staticmethod
    def _fallbackRetryDelay(error: str | None) -> float:
        """Parse provider retry guidance; use a short default when absent."""

        text = str(error or "")
        for pattern in (r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", r"retry in\s+([0-9.]+)s"):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                try:
                    return max(5.0, min(float(match.group(1)), 300.0))
                except Exception:
                    continue
        return 60.0

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
                "429",
                "resource_exhausted",
                "quota",
                "rate limit",
                "rate-limit",
            )
        )

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        """Read config values from Aura's dot-path config interface."""

        if config is None:
            return default
        return config.get(key, default)

    @staticmethod
    def _normalizeProviderName(providerName) -> str:
        """Normalize disabled provider config values to an empty provider name."""

        name = str(providerName or "").strip().lower()
        if name in {"", "none", "disabled", "off", "false", "null"}:
            return ""
        return name
