"""SQLite persistence for Aura's unified personal schedule hub."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

from modules.personalSchedule.models import ScheduleItem


class SQLiteScheduleStore:
    """Persist schedule items, timers, and recurrence rules."""

    def __init__(self, databasePath: str):
        self.databasePath = str(databasePath or "aura_schedule.sqlite3")
        self._lock = RLock()
        self._connection = sqlite3.connect(self.databasePath, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._ensureSchema()

    def shutdown(self):
        with self._lock:
            try:
                self._connection.close()
            except Exception:
                pass

    def upsertItem(self, item: ScheduleItem):
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO schedule_items (
                    item_id, title, description, item_type, start_time, end_time, due_time,
                    priority, tags, state, recurrence_rule, created_at, updated_at,
                    metadata, source, requires_acknowledgement
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    item_type=excluded.item_type,
                    start_time=excluded.start_time,
                    end_time=excluded.end_time,
                    due_time=excluded.due_time,
                    priority=excluded.priority,
                    tags=excluded.tags,
                    state=excluded.state,
                    recurrence_rule=excluded.recurrence_rule,
                    updated_at=excluded.updated_at,
                    metadata=excluded.metadata,
                    source=excluded.source,
                    requires_acknowledgement=excluded.requires_acknowledgement
                """,
                (
                    item.itemId,
                    item.title,
                    item.description,
                    item.type.value,
                    item.startTime,
                    item.endTime,
                    item.dueTime,
                    item.priority,
                    self._encode(item.tags),
                    item.state.value,
                    self._encode(item.recurrenceRule.asDict() if item.recurrenceRule else None),
                    item.createdAt,
                    item.updatedAt,
                    self._encode(item.metadata),
                    item.source,
                    int(bool(item.requiresAcknowledgement)),
                ),
            )
            self._connection.commit()
        return item

    def deleteItem(self, itemId: str):
        with self._lock:
            self._connection.execute("DELETE FROM schedule_items WHERE item_id = ?", (str(itemId),))
            self._connection.commit()

    def getItem(self, itemId: str) -> ScheduleItem | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM schedule_items WHERE item_id = ?", (str(itemId),)).fetchone()
        return self._rowToItem(row) if row else None

    def listItems(self) -> list[ScheduleItem]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM schedule_items ORDER BY COALESCE(start_time, due_time, created_at) ASC").fetchall()
        return [self._rowToItem(row) for row in rows if row is not None]

    def listItemsByType(self, itemType: str) -> list[ScheduleItem]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM schedule_items WHERE item_type = ? ORDER BY COALESCE(start_time, due_time, created_at) ASC", (str(itemType),)).fetchall()
        return [self._rowToItem(row) for row in rows if row is not None]

    def listItemsByState(self, state: str) -> list[ScheduleItem]:
        with self._lock:
            rows = self._connection.execute("SELECT * FROM schedule_items WHERE state = ? ORDER BY COALESCE(start_time, due_time, created_at) ASC", (str(state),)).fetchall()
        return [self._rowToItem(row) for row in rows if row is not None]

    def searchItems(self, query: str, limit: int = 20) -> list[ScheduleItem]:
        """Return items matching the supplied text query."""

        needle = str(query or "").strip().lower()
        if not needle:
            return self.listItems()[: int(limit)]

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM schedule_items
                WHERE lower(title) LIKE ? OR lower(description) LIKE ? OR lower(tags) LIKE ?
                ORDER BY COALESCE(start_time, due_time, created_at) ASC
                """,
                (f"%{needle}%", f"%{needle}%", f"%{needle}%"),
            ).fetchall()
        return [self._rowToItem(row) for row in rows if row is not None][: int(limit)]

    def listDueItems(self, atIso: str) -> list[ScheduleItem]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM schedule_items
                WHERE state IN ('PENDING', 'ACTIVE', 'SNOOZED')
                  AND (
                        (due_time IS NOT NULL AND due_time != '' AND due_time <= ?)
                     OR (start_time IS NOT NULL AND start_time != '' AND start_time <= ?)
                     OR (item_type = 'TIMER' AND end_time IS NOT NULL AND end_time != '' AND end_time <= ?)
                  )
                ORDER BY COALESCE(due_time, start_time, end_time, created_at) ASC
                """,
                (atIso, atIso, atIso),
            ).fetchall()
        return [self._rowToItem(row) for row in rows if row is not None]

    def listOverdueItems(self, atIso: str) -> list[ScheduleItem]:
        """Return overdue items that should be surfaced to the user."""

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM schedule_items
                WHERE state IN ('PENDING', 'ACTIVE', 'SNOOZED')
                  AND (
                        (due_time IS NOT NULL AND due_time != '' AND due_time < ?)
                     OR (start_time IS NOT NULL AND start_time != '' AND start_time < ?)
                  )
                ORDER BY COALESCE(due_time, start_time, created_at) ASC
                """,
                (atIso, atIso),
            ).fetchall()
        return [self._rowToItem(row) for row in rows if row is not None]

    def _ensureSchema(self):
        with self._lock:
            Path(self.databasePath).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_items (
                    item_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    item_type TEXT NOT NULL,
                    start_time TEXT NOT NULL DEFAULT '',
                    end_time TEXT NOT NULL DEFAULT '',
                    due_time TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'NORMAL',
                    tags TEXT NOT NULL DEFAULT '[]',
                    state TEXT NOT NULL DEFAULT 'PENDING',
                    recurrence_rule TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    source TEXT NOT NULL DEFAULT '',
                    requires_acknowledgement INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._connection.commit()

    @staticmethod
    def _encode(value: Any) -> str:
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def _decode(value: str | None, default):
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    def _rowToItem(self, row) -> ScheduleItem:
        data = dict(row)
        data["tags"] = self._decode(data.get("tags"), [])
        data["metadata"] = self._decode(data.get("metadata"), {})
        data["recurrenceRule"] = self._decode(data.get("recurrence_rule"), None)
        data["recurrence_rule"] = data["recurrenceRule"]
        data["type"] = data.get("item_type")
        data["state"] = data.get("state")
        data["itemId"] = data.get("item_id")
        data["startTime"] = data.get("start_time")
        data["endTime"] = data.get("end_time")
        data["dueTime"] = data.get("due_time")
        data["createdAt"] = data.get("created_at")
        data["updatedAt"] = data.get("updated_at")
        data["requiresAcknowledgement"] = bool(data.get("requires_acknowledgement"))
        return ScheduleItem.fromDict(data)
