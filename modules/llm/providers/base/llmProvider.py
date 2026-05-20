"""Abstract provider interface for Aura LLM integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from modules.llm.models.llmResponse import LLMResponse
from modules.llm.providers.base.providerCapabilities import ProviderCapabilities


class LLMProvider(ABC):
    """Provider contract used by the model-agnostic LLM manager."""

    providerName = "base"
    capabilities = ProviderCapabilities()

    def __init__(self, context=None):
        """Store shared context and prepare provider-local state."""

        self.context = context
        self.logger = None
        self.initialized = False

    @abstractmethod
    def initialize(self):
        """Initialize provider resources."""

    @abstractmethod
    def shutdown(self):
        """Release provider resources."""

    @abstractmethod
    def generateResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Generate a normal text response."""

    @abstractmethod
    def generateStructuredResponse(
        self,
        systemPrompt: str,
        userPrompt: str,
        schema: dict,
        conversationHistory: list | None = None,
    ) -> LLMResponse:
        """Generate a JSON response that satisfies the supplied schema."""

    def getCapabilities(self) -> ProviderCapabilities:
        """Return provider feature support."""

        return self.capabilities
