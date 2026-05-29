"""Deterministic local embedding provider for Aura."""

from __future__ import annotations

import hashlib
import math
from typing import Iterable

from providers.embeddings.embeddingProvider import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """A lightweight local embedding provider with small semantic expansion."""

    providerName = "local"

    semanticExpansions = {
        "working": ("working", "developing", "building", "project", "task"),
        "working on": ("working", "developing", "building", "project", "task"),
        "work": ("working", "developing", "building", "project", "task"),
        "developing": ("working", "developing", "building", "project", "task"),
        "developed": ("working", "developing", "building", "project", "task"),
        "building": ("working", "developing", "building", "project", "task"),
        "project": ("project", "work", "task", "development"),
        "pipeline": ("project", "workflow", "work", "development"),
        "yesterday": ("recent", "recently", "past", "yesterday"),
        "today": ("current", "now", "recent", "present"),
        "voice": ("voice", "speech", "audio", "mic"),
        "music": ("music", "spotify", "audio", "media"),
        "calendar": ("calendar", "schedule", "event", "appointment"),
        "email": ("email", "mail", "message", "inbox"),
        "lighting": ("lighting", "lights", "brightness", "illumination"),
        "home": ("home", "house", "smart", "device"),
        "security": ("security", "safety", "motion", "alarm"),
    }

    def __init__(self, context=None, dimensions: int = 128):
        super().__init__(context=context)
        self.vectorDimensions = int(dimensions)
        self.modelName = f"local-hash-{self.vectorDimensions}"

    def initialize(self):
        self.logger = getattr(getattr(self.context, "logger", None), "getChild", lambda *_args, **_kwargs: None)("Embeddings.Local") if self.context else None
        self.initialized = True
        return self

    def embedText(self, text: str) -> list[float]:
        tokens = self._semanticTokens(text)
        vector = [0.0] * self.vectorDimensions
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.vectorDimensions
            weight = 1.0 + (len(token) / 24.0)
            vector[index] += weight
        return self._normalize(vector)

    def isAvailable(self) -> bool:
        return True

    def shutdown(self):
        self.initialized = False

    def embedBatch(self, texts: list[str]) -> list[list[float]]:
        return [self.embedText(text) for text in texts]

    def _semanticTokens(self, text: str) -> list[str]:
        cleaned = "".join(character.lower() if character.isalnum() else " " for character in str(text or ""))
        rawTokens = [token for token in cleaned.split() if token]
        expanded: list[str] = []
        for token in rawTokens:
            expanded.append(token)
            if token in self.semanticExpansions:
                expanded.extend(self.semanticExpansions[token])
        joined = " ".join(rawTokens)
        for phrase, tokens in self.semanticExpansions.items():
            if phrase in joined:
                expanded.extend(tokens)
        return expanded

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
