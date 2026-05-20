"""Provider capability metadata for LLM backends."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    """Feature support advertised by a model provider."""

    supportsStructuredOutput: bool = False
    supportsStreaming: bool = False
    supportsVision: bool = False
    supportsFileSearch: bool = False
    supportsUrlContext: bool = False
    supportsToolCalling: bool = False
    supportsComputerUse: bool = False
    supportsCodeExecution: bool = False

    def asDict(self):
        """Return capabilities as a serializable dictionary."""

        return {
            "supportsStructuredOutput": self.supportsStructuredOutput,
            "supportsStreaming": self.supportsStreaming,
            "supportsVision": self.supportsVision,
            "supportsFileSearch": self.supportsFileSearch,
            "supportsUrlContext": self.supportsUrlContext,
            "supportsToolCalling": self.supportsToolCalling,
            "supportsComputerUse": self.supportsComputerUse,
            "supportsCodeExecution": self.supportsCodeExecution,
        }
