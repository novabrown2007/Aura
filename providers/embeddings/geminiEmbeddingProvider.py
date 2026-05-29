"""Gemini-backed embedding provider for Aura."""

from __future__ import annotations

from typing import Any

from providers.embeddings.embeddingProvider import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Generate embeddings with Google's Gemini API when configured."""

    providerName = "gemini"

    def __init__(self, context=None, model: str = "text-embedding-004", outputDimensionality: int | None = None):
        super().__init__(context=context)
        self.modelName = str(model or "text-embedding-004")
        self.outputDimensionality = int(outputDimensionality) if outputDimensionality else None
        self.client = None
        self.apiKey = ""

    def initialize(self):
        config = getattr(self.context, "config", None)
        logger = getattr(self.context, "logger", None)
        self.logger = logger.getChild("Embeddings.Gemini") if logger else None
        self.apiKey = self._getConfigValue(config, "llm.gemini.api_secret", "") or self._getConfigValue(config, "llm.gemini.apiKey", "")
        self.apiKey = self.apiKey or self._getConfigValue(config, "semanticMemory.embeddingApiKey", "")
        if not self.apiKey:
            self.initialized = False
            return self

        try:
            from google import genai
        except ImportError as error:
            self.initialized = False
            if self.logger:
                self.logger.warning(f"Gemini embedding SDK unavailable: {error}")
            return self

        try:
            self.client = genai.Client(api_key=self.apiKey)
            self.initialized = True
        except Exception as error:
            self.client = None
            self.initialized = False
            if self.logger:
                self.logger.warning(f"Gemini embedding client could not initialize: {error}")
        return self

    def embedText(self, text: str) -> list[float]:
        if not self.isAvailable():
            return []
        response = self._embed([str(text or "")])
        return self._extractVector(response, 0)

    def embedBatch(self, texts: list[str]) -> list[list[float]]:
        if not self.isAvailable():
            return [[] for _ in texts]
        response = self._embed([str(text or "") for text in texts])
        embeddings = getattr(response, "embeddings", None) or []
        vectors = []
        for index in range(len(texts)):
            vectors.append(self._extractVector(response, index))
        return vectors

    def isAvailable(self) -> bool:
        return bool(self.initialized and self.client is not None)

    def shutdown(self):
        self.client = None
        self.initialized = False

    def _embed(self, texts: list[str]):
        config: dict[str, Any] = {"task_type": "SEMANTIC_SIMILARITY"}
        if self.outputDimensionality:
            config["output_dimensionality"] = int(self.outputDimensionality)
        return self.client.models.embed_content(
            model=self.modelName,
            contents=texts if len(texts) > 1 else texts[0],
            config=config,
        )

    @staticmethod
    def _extractVector(response, index: int) -> list[float]:
        embeddings = getattr(response, "embeddings", None) or []
        if index >= len(embeddings):
            return []
        embedding = embeddings[index]
        values = getattr(embedding, "values", None)
        if values is None:
            values = embedding.get("values") if isinstance(embedding, dict) else []
        return [float(value) for value in (values or [])]

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
