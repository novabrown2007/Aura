"""SQLite-backed embedding storage for Aura semantic memory."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from assistant.memory.models import MemoryEmbedding


class SQLiteEmbeddingStore:
    """Persist memory embeddings alongside Aura's structured memory store."""

    def __init__(self, databasePath: str = "aura_memory.sqlite3", context=None):
        self.databasePath = Path(databasePath)
        self.context = context
        self.logger = self._getLogger(context)
        self.connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self.connect()
        self.initializeSchema()

    def connect(self):
        if self.connection is not None:
            return
        self.databasePath.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.databasePath), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

    def initializeSchema(self):
        with self._lock:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    embedding_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL UNIQUE,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    vector TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_embeddings_memory_id ON memory_embeddings(memory_id)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_embeddings_provider ON memory_embeddings(provider)")
            self.connection.commit()

    def upsertEmbedding(self, embedding: MemoryEmbedding) -> MemoryEmbedding:
        with self._lock:
            self.connection.execute(
                """
                INSERT INTO memory_embeddings (
                    embedding_id, memory_id, provider, model, vector,
                    created_at, updated_at, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    provider = excluded.provider,
                    model = excluded.model,
                    vector = excluded.vector,
                    updated_at = excluded.updated_at,
                    metadata = excluded.metadata
                """,
                (
                    embedding.embeddingId,
                    embedding.memoryId,
                    embedding.provider,
                    embedding.model,
                    json.dumps(list(embedding.vector), sort_keys=True),
                    embedding.createdAt,
                    embedding.updatedAt,
                    json.dumps(dict(embedding.metadata), sort_keys=True),
                ),
            )
            self.connection.commit()
        return embedding

    def getEmbeddingByMemoryId(self, memoryId: str) -> MemoryEmbedding | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM memory_embeddings WHERE memory_id = ?",
                (str(memoryId),),
            ).fetchone()
        return self._fromRow(row) if row else None

    def listEmbeddings(self) -> list[MemoryEmbedding]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM memory_embeddings ORDER BY updated_at DESC, memory_id DESC"
            ).fetchall()
        return [self._fromRow(row) for row in rows]

    def deleteEmbedding(self, memoryId: str) -> bool:
        with self._lock:
            cursor = self.connection.execute(
                "DELETE FROM memory_embeddings WHERE memory_id = ?",
                (str(memoryId),),
            )
            self.connection.commit()
        return cursor.rowcount > 0

    def clear(self):
        with self._lock:
            self.connection.execute("DELETE FROM memory_embeddings")
            self.connection.commit()

    def count(self) -> int:
        with self._lock:
            row = self.connection.execute("SELECT COUNT(*) AS count FROM memory_embeddings").fetchone()
        return int(row["count"])

    def snapshot(self) -> dict[str, Any]:
        return {
            "databasePath": str(self.databasePath),
            "count": self.count(),
            "provider": "",
        }

    def close(self):
        if self.connection is None:
            return
        with self._lock:
            self.connection.close()
            self.connection = None

    @staticmethod
    def _fromRow(row) -> MemoryEmbedding:
        return MemoryEmbedding.fromDict(
            {
                "embeddingId": row["embedding_id"],
                "memoryId": row["memory_id"],
                "provider": row["provider"],
                "model": row["model"],
                "vector": json.loads(row["vector"] or "[]"),
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "metadata": json.loads(row["metadata"] or "{}"),
            }
        )

    @staticmethod
    def _getLogger(context):
        logger = getattr(context, "logger", None)
        return logger.getChild("Memory.EmbeddingStore") if logger else None
