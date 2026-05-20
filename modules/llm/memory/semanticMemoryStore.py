"""Database-backed semantic memory store for Aura."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from modules.llm.memory.embeddingProvider import EmbeddingProvider


class SemanticMemoryStore:
    """Store and retrieve long-term memories with semantic ranking."""

    def __init__(self, database, embeddingProvider: EmbeddingProvider | None = None):
        """Bind the store to a database adapter."""

        self.database = database
        self.embeddingProvider = embeddingProvider or EmbeddingProvider()

    def upsertMemory(
        self,
        memoryKey: str,
        content: str,
        summary: str = "",
        memoryType: str = "fact",
        topics: list[str] | None = None,
        relationships: dict[str, Any] | None = None,
        importance: int = 1,
        source: str = "memory",
    ):
        """Create or replace a semantic memory record."""

        if not self.database:
            return

        textForEmbedding = " ".join(
            part for part in [memoryKey, content, summary, " ".join(topics or [])] if part
        )
        embedding = self.embeddingProvider.embedText(textForEmbedding)
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        self.database.execute(
            "DELETE FROM semantic_memory WHERE memory_key = ?",
            (str(memoryKey),),
        )
        self.database.execute(
            """
            INSERT INTO semantic_memory (
                memory_key, content, summary, memory_type, topics,
                relationships, importance, source, embedding, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(memoryKey),
                str(content),
                str(summary or content),
                str(memoryType),
                json.dumps(topics or []),
                json.dumps(relationships or {}),
                int(importance),
                str(source),
                json.dumps(embedding),
                now,
            ),
        )

    def search(self, query: str, limit: int = 5, minScore: float = 0.0) -> list[dict[str, Any]]:
        """Return memories ranked by semantic similarity and importance."""

        if not self.database:
            return []

        queryVector = self.embeddingProvider.embedText(query)
        rows = self.database.fetchAll(
            """
            SELECT memory_key, content, summary, memory_type, topics,
                   relationships, importance, source, embedding, updated_at
            FROM semantic_memory
            """
        )
        ranked = []
        for row in rows:
            embedding = self._loadJson(row.get("embedding"), [])
            score = self.embeddingProvider.cosineSimilarity(queryVector, embedding)
            importance = int(row.get("importance") or 1)
            finalScore = score + (importance * 0.03)
            if finalScore < minScore:
                continue
            ranked.append(
                {
                    "memory_key": row.get("memory_key"),
                    "content": row.get("content"),
                    "summary": row.get("summary"),
                    "memory_type": row.get("memory_type"),
                    "topics": self._loadJson(row.get("topics"), []),
                    "relationships": self._loadJson(row.get("relationships"), {}),
                    "importance": importance,
                    "source": row.get("source"),
                    "updated_at": row.get("updated_at"),
                    "score": finalScore,
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[: int(limit)]

    def delete(self, memoryKey: str):
        """Delete a semantic memory by key."""

        if self.database:
            self.database.execute("DELETE FROM semantic_memory WHERE memory_key = ?", (memoryKey,))

    def clear(self):
        """Clear all semantic memories."""

        if self.database:
            self.database.execute("DELETE FROM semantic_memory")

    @staticmethod
    def _loadJson(value, default):
        """Parse a JSON field defensively."""

        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return default
