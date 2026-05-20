"""Initialize the `modules.llm` package and expose package-level integration points."""

"""LLM support package metadata for Aura."""

from modules.llm.llmHandler import LLMHandler
from modules.llm.manager.llmManager import LLMManager


MODULE_METADATA = LLMHandler.metadata

__all__ = ["LLMHandler", "LLMManager", "MODULE_METADATA"]
