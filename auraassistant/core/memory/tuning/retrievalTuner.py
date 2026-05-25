"""Configuration-backed tuning for Aura memory retrieval."""

from __future__ import annotations


class RetrievalTuner:
    """Expose deterministic retrieval weights, limits, and debug settings."""

    defaultCategoryWeights = {
        "tasks": 1.25,
        "projects": 1.18,
        "preferences": 1.08,
        "assistant_context": 1.06,
        "system_context": 1.0,
        "habits": 0.96,
        "people": 0.94,
        "locations": 0.9,
        "reminders": 0.88,
        "conversation_summaries": 0.72,
    }

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.RetrievalTuner") if logger else None
        config = getattr(context, "config", None)
        self.injectionEnabled = self._bool(config, "memoryInjectionEnabled", self._bool(config, "memory.injectionEnabled", True))
        self.maxInjectionCount = self._int(config, "memoryMaxInjectionCount", self._int(config, "memory.maxInjectionCount", 5))
        self.maxInjectionCharacters = self._int(config, "memoryMaxInjectionCharacters", self._int(config, "memory.maxInjectionCharacters", 900))
        self.recencyWeight = self._float(config, "memoryRecencyWeight", self._float(config, "memory.recencyWeight", 0.18))
        self.importanceWeight = self._float(config, "memoryImportanceWeight", self._float(config, "memory.importanceWeight", 0.24))
        self.duplicateFiltering = self._bool(config, "memoryDuplicateFiltering", self._bool(config, "memory.duplicateFiltering", True))
        self.compressionEnabled = self._bool(config, "memoryCompressionEnabled", self._bool(config, "memory.compressionEnabled", True))
        self.minRelevance = self._float(config, "memoryMinRelevance", self._float(config, "memory.minRelevance", 0.18))
        self.candidateLimit = self._int(config, "memoryRetrievalCandidateLimit", self._int(config, "memory.retrievalCandidateLimit", 24))
        self.debugEnabled = self._bool(config, "memoryRetrievalDebug", self._bool(config, "memory.retrievalDebug", True))
        self.categoryWeights = dict(self.defaultCategoryWeights)
        configured = self._value(config, "memory.categoryWeights", {})
        if isinstance(configured, dict):
            for category, weight in configured.items():
                try:
                    self.categoryWeights[str(category)] = float(weight)
                except Exception:
                    continue

    def metrics(self) -> dict:
        """Return current tuning values for debugging output."""

        return {
            "injectionEnabled": self.injectionEnabled,
            "maxInjectionCount": self.maxInjectionCount,
            "maxInjectionCharacters": self.maxInjectionCharacters,
            "recencyWeight": self.recencyWeight,
            "importanceWeight": self.importanceWeight,
            "duplicateFiltering": self.duplicateFiltering,
            "compressionEnabled": self.compressionEnabled,
            "minRelevance": self.minRelevance,
            "candidateLimit": self.candidateLimit,
            "debugEnabled": self.debugEnabled,
            "categoryWeights": dict(self.categoryWeights),
        }

    @staticmethod
    def _value(config, key: str, default=None):
        if config is None:
            return default
        return config.get(key, default)

    @classmethod
    def _bool(cls, config, key: str, default=False) -> bool:
        value = cls._value(config, key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def _int(cls, config, key: str, default=0) -> int:
        try:
            return int(cls._value(config, key, default))
        except Exception:
            return int(default)

    @classmethod
    def _float(cls, config, key: str, default=0.0) -> float:
        try:
            return float(cls._value(config, key, default))
        except Exception:
            return float(default)

