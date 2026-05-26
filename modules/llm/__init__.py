"""LLM support package metadata for Aura.

Keep this package initializer lightweight. Subpackages such as
``modules.llm.memory`` should be importable without loading provider clients.
"""

from modules.base import ModuleMetadata


MODULE_METADATA = ModuleMetadata(
    name="llm",
    version="1.4.0",
    description="Provider-neutral LLM prompt handling and response generation.",
    permissions=("network:http", "database:read", "database:write"),
    capabilities=("conversation", "memory", "llm"),
)

__all__ = ["LLMHandler", "LLMManager", "MODULE_METADATA"]


def __getattr__(name: str):
    """Lazily expose heavy LLM runtime classes."""

    if name == "LLMHandler":
        from modules.llm.llmHandler import LLMHandler

        return LLMHandler
    if name == "LLMManager":
        from modules.llm.manager.llmManager import LLMManager

        return LLMManager
    raise AttributeError(f"module 'modules.llm' has no attribute {name!r}")
