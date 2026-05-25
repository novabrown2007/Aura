"""SQLite-backed persistence for Aura's structured memory layer."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.memory.memoryStore import MemoryStore
from core.memory.models import Memory, MemoryCategory, MemoryQuery
from core.memory.models.memory import utcNow


class SQLiteMemoryStore(MemoryStore):
    """Persist structured memories in a local SQLite database."""

    def __init__(self, databasePath: str = "aura_memory.sqlite3", context=None):
        self.databasePath = Path(databasePath)
        self.context = context
        self.logger = self._getLogger(context)
        self.connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self.connect()
        self.initializeSchema()

    def connect(self):
        """Open the SQLite database if needed."""

        if self.connection is not None:
            return
        self.databasePath.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.databasePath), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        if self.logger:
            self.logger.info(f"Memory SQLite connected: {self.databasePath}")

    def close(self):
        """Close the SQLite connection."""

        if self.connection is None:
            return
        with self._lock:
            self.connection.close()
            self.connection = None

    def initializeSchema(self):
        """Create memory tables and deterministic lookup indexes."""

        with self._lock:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS structured_memories (
                    memory_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT,
                    session_id TEXT,
                    metadata TEXT
                )
                """
            )
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON structured_memories(category)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON structured_memories(importance)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated_at ON structured_memories(updated_at)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memories_session ON structured_memories(session_id)")
            self.connection.commit()

    def upsertMemory(self, memory: Memory) -> Memory:
        """Create or update a memory row."""

        memory.updatedAt = utcNow()
        with self._lock:
            self.connection.execute(
                """
                INSERT INTO structured_memories (
                    memory_id, category, title, content, tags, importance,
                    created_at, updated_at, source, session_id, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    category = excluded.category,
                    title = excluded.title,
                    content = excluded.content,
                    tags = excluded.tags,
                    importance = excluded.importance,
                    updated_at = excluded.updated_at,
                    source = excluded.source,
                    session_id = excluded.session_id,
                    metadata = excluded.metadata
                """,
                self._toRow(memory),
            )
            self.connection.commit()
        if self.logger:
            self.logger.info(f"Memory stored: {memory.category}:{memory.title}")
        return memory

    def getMemory(self, memoryId: str) -> Memory | None:
        """Return one memory by id."""

        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM structured_memories WHERE memory_id = ?",
                (memoryId,),
            ).fetchone()
        return self._fromRow(row) if row else None

    def deleteMemory(self, memoryId: str) -> bool:
        """Delete one memory."""

        with self._lock:
            cursor = self.connection.execute(
                "DELETE FROM structured_memories WHERE memory_id = ?",
                (memoryId,),
            )
            self.connection.commit()
        deleted = cursor.rowcount > 0
        if deleted and self.logger:
            self.logger.info(f"Memory deleted: {memoryId}")
        return deleted

    def queryMemories(self, query: MemoryQuery | None = None) -> list[Memory]:
        """Return memories matching structured filters."""

        query = query or MemoryQuery()
        clauses = []
        params: list[Any] = []

        if query.categories:
            categories = [MemoryCategory.normalize(category) for category in query.categories]
            clauses.append(f"category IN ({','.join('?' for _ in categories)})")
            params.extend(categories)

        if query.minImportance is not None:
            clauses.append("importance >= ?")
            params.append(float(query.minImportance))

        if query.sessionId:
            clauses.append("session_id = ?")
            params.append(query.sessionId)

        if query.recentDays is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=int(query.recentDays))
            clauses.append("updated_at >= ?")
            params.append(cutoff.replace(microsecond=0).isoformat())

        sql = "SELECT * FROM structured_memories"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY importance DESC, updated_at DESC"
        if query.limit:
            sql += " LIMIT ?"
            params.append(int(query.limit))

        with self._lock:
            rows = self.connection.execute(sql, tuple(params)).fetchall()
        memories = [self._fromRow(row) for row in rows]

        tags = set(query.normalizedTags())
        if tags:
            memories = [memory for memory in memories if tags.intersection(memory.tags)]

        keywords = str(query.keywords or "").strip().lower()
        if keywords:
            tokens = {token for token in keywords.split() if token}
            memories = [
                memory for memory in memories
                if any(token in f"{memory.title} {memory.content} {' '.join(memory.tags)}".lower() for token in tokens)
            ]

        return memories[: query.limit] if query.limit else memories

    def pruneMemories(self, minImportance: float, limit: int | None = None) -> int:
        """Delete low-importance memories, oldest first."""

        sql = "SELECT memory_id FROM structured_memories WHERE importance < ? ORDER BY updated_at ASC"
        params: list[Any] = [float(minImportance)]
        if limit:
            sql += " LIMIT ?"
            params.append(int(limit))
        with self._lock:
            rows = self.connection.execute(sql, tuple(params)).fetchall()
            ids = [row["memory_id"] for row in rows]
            for memoryId in ids:
                self.connection.execute("DELETE FROM structured_memories WHERE memory_id = ?", (memoryId,))
            self.connection.commit()
        if ids and self.logger:
            self.logger.info(f"Pruned {len(ids)} low-importance memories")
        return len(ids)

    def count(self) -> int:
        """Return total memory count."""

        with self._lock:
            row = self.connection.execute("SELECT COUNT(*) AS count FROM structured_memories").fetchone()
        return int(row["count"])

    @staticmethod
    def _toRow(memory: Memory) -> tuple:
        return (
            memory.memoryId,
            memory.category,
            memory.title,
            memory.content,
            json.dumps(memory.tags, sort_keys=True),
            memory.importance,
            memory.createdAt,
            memory.updatedAt,
            memory.source,
            memory.sessionId,
            json.dumps(memory.metadata, sort_keys=True),
        )

    @staticmethod
    def _fromRow(row) -> Memory:
        return Memory.fromDict(
            {
                "memoryId": row["memory_id"],
                "category": row["category"],
                "title": row["title"],
                "content": row["content"],
                "tags": json.loads(row["tags"] or "[]"),
                "importance": row["importance"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "source": row["source"],
                "sessionId": row["session_id"],
                "metadata": json.loads(row["metadata"] or "{}"),
            }
        )

    @staticmethod
    def _getLogger(context):
        logger = getattr(context, "logger", None)
        return logger.getChild("Memory.SQLiteStore") if logger else None

