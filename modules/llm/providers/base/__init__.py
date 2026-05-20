"""Base provider contract."""

from modules.llm.providers.base.llmProvider import LLMProvider
from modules.llm.providers.base.providerCapabilities import ProviderCapabilities

__all__ = ["LLMProvider", "ProviderCapabilities"]
