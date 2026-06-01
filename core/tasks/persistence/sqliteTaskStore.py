"""SQLite-backed storage for Aura task orchestration."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable


class SQLiteTaskStore:
    """Persist lightweight task state across restarts."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self):
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                state TEXT NOT NULL,
                priority TEXT NOT NULL,
                created_at TEXT,
                scheduled_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                retry_policy TEXT,
                execution_context TEXT,
                metadata TEXT,
                attempts INTEGER DEFAULT 0,
                next_run_at TEXT,
                last_error TEXT,
                result TEXT,
                recurring_task TEXT,
                cancel_requested INTEGER DEFAULT 0,
                run_count INTEGER DEFAULT 0
            )
            """
        )
        self.connection.commit()

    def upsertTask(self, task: dict):
        payload = dict(task or {})
        self.connection.execute(
            """
            INSERT INTO tasks (
                task_id, task_name, task_type, state, priority, created_at,
                scheduled_at, started_at, completed_at, retry_policy,
                execution_context, metadata, attempts, next_run_at, last_error,
                result, recurring_task, cancel_requested, run_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                task_name=excluded.task_name,
                task_type=excluded.task_type,
                state=excluded.state,
                priority=excluded.priority,
                created_at=excluded.created_at,
                scheduled_at=excluded.scheduled_at,
                started_at=excluded.started_at,
                completed_at=excluded.completed_at,
                retry_policy=excluded.retry_policy,
                execution_context=excluded.execution_context,
                metadata=excluded.metadata,
                attempts=excluded.attempts,
                next_run_at=excluded.next_run_at,
                last_error=excluded.last_error,
                result=excluded.result,
                recurring_task=excluded.recurring_task,
                cancel_requested=excluded.cancel_requested,
                run_count=excluded.run_count
            """,
            (
                str(payload.get("taskId") or ""),
                str(payload.get("taskName") or ""),
                str(payload.get("taskType") or ""),
                str(payload.get("state") or ""),
                str(payload.get("priority") or ""),
                payload.get("createdAt"),
                payload.get("scheduledAt"),
                payload.get("startedAt"),
                payload.get("completedAt"),
                self._dump(payload.get("retryPolicy")),
                self._dump(payload.get("executionContext")),
                self._dump(payload.get("metadata")),
                int(payload.get("attempts") or 0),
                payload.get("nextRunAt"),
                str(payload.get("lastError") or ""),
                self._dump(payload.get("result")),
                self._dump(payload.get("recurringTask")),
                1 if payload.get("cancelRequested") else 0,
                int(payload.get("runCount") or 0),
            ),
        )
        self.connection.commit()

    def deleteTask(self, taskId: str):
        self.connection.execute("DELETE FROM tasks WHERE task_id = ?", (str(taskId),))
        self.connection.commit()

    def loadTask(self, taskId: str) -> dict | None:
        row = self.connection.execute("SELECT * FROM tasks WHERE task_id = ?", (str(taskId),)).fetchone()
        return self._rowToDict(row)

    def loadTasks(self, states: Iterable[str] | None = None) -> list[dict]:
        if states:
            placeholders = ",".join("?" for _ in states)
            rows = self.connection.execute(
                f"SELECT * FROM tasks WHERE state IN ({placeholders}) ORDER BY scheduled_at ASC, created_at ASC",
                tuple(str(item) for item in states),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM tasks ORDER BY scheduled_at ASC, created_at ASC"
            ).fetchall()
        return [self._rowToDict(row) for row in rows if row is not None]

    def clear(self):
        self.connection.execute("DELETE FROM tasks")
        self.connection.commit()

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass

    @staticmethod
    def _dump(value):
        try:
            return json.dumps(value if value is not None else {}, sort_keys=True)
        except TypeError:
            return json.dumps(str(value), sort_keys=True)

    @staticmethod
    def _load(value):
        if value in (None, ""):
            return {}
        if isinstance(value, (dict, list, int, float, bool)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return value

    def _rowToDict(self, row):
        if row is None:
            return None
        payload = dict(row)
        payload["retryPolicy"] = self._load(payload.get("retry_policy"))
        payload["executionContext"] = self._load(payload.get("execution_context"))
        payload["metadata"] = self._load(payload.get("metadata"))
        payload["result"] = self._load(payload.get("result"))
        payload["recurringTask"] = self._load(payload.get("recurring_task"))
        return {
            "taskId": payload.get("task_id"),
            "taskName": payload.get("task_name"),
            "taskType": payload.get("task_type"),
            "state": payload.get("state"),
            "priority": payload.get("priority"),
            "createdAt": payload.get("created_at"),
            "scheduledAt": payload.get("scheduled_at"),
            "startedAt": payload.get("started_at"),
            "completedAt": payload.get("completed_at"),
            "retryPolicy": payload.get("retryPolicy"),
            "executionContext": payload.get("executionContext"),
            "metadata": payload.get("metadata"),
            "attempts": payload.get("attempts"),
            "nextRunAt": payload.get("next_run_at"),
            "lastError": payload.get("last_error"),
            "result": payload.get("result"),
            "recurringTask": payload.get("recurringTask"),
            "cancelRequested": bool(payload.get("cancel_requested")),
            "runCount": payload.get("run_count"),
        }
