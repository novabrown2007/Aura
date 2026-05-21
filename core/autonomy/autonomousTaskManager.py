"""Persistent autonomous task orchestration for Aura."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Callable

from core.threading.scheduler.schedule import Schedule
from core.threading.tasks.task import Task


class AutonomousTaskManager:
    """
    Manages long-running assistant tasks with persistence and scheduled wakeups.

    Autonomous tasks are durable task definitions such as "watch GPU prices" or
    "check weather each morning". The manager stores state in the database,
    wakes active tasks on a schedule, and dispatches each wakeup through a
    registered handler plus lifecycle events.
    """

    POLL_SCHEDULE_NAME = "autonomous_tasks_poll"

    def __init__(self, context):
        """Initialize the manager and register scheduler/event hooks."""

        self.context = context
        self.database = getattr(context, "database", None)
        self.logger = context.logger.getChild("Autonomy") if getattr(context, "logger", None) else None
        self.handlers: dict[str, Callable[[dict], object]] = {}

        self._initializeDatabase()
        self._subscribeToEvents()
        self._registerWakeupSchedule()

    def _initializeDatabase(self):
        """Ensure autonomous task persistence exists when a database is available."""

        if self.database is None:
            return

        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS autonomous_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                task_type VARCHAR(128) NOT NULL,
                description TEXT,
                status VARCHAR(32) DEFAULT 'active',
                interval_seconds INT NULL,
                next_run_at DATETIME NULL,
                last_run_at DATETIME NULL,
                event_name VARCHAR(255) NULL,
                state TEXT,
                memory_context TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )

    def _subscribeToEvents(self):
        """Subscribe to generic task control events."""

        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is None:
            return

        event_manager.subscribe("autonomous.task.create", self._handleCreateEvent)
        event_manager.subscribe("autonomous.task.pause", self._handlePauseEvent)
        event_manager.subscribe("autonomous.task.resume", self._handleResumeEvent)
        event_manager.subscribe("autonomous.task.run", self._handleRunEvent)

    def _registerWakeupSchedule(self):
        """Register periodic due-task polling with the runtime scheduler."""

        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is None or scheduler.getSchedule(self.POLL_SCHEDULE_NAME) is not None:
            return

        scheduler.addSchedule(
            Schedule(
                name=self.POLL_SCHEDULE_NAME,
                target=self.wakeDueTasks,
                interval=30.0,
            )
        )

    def registerHandler(self, task_type: str, handler: Callable[[dict], object]):
        """Register an in-process handler for one autonomous task type."""

        self.handlers[str(task_type)] = handler

    def createTask(
        self,
        name: str,
        task_type: str,
        description: str = "",
        interval_seconds: int | None = None,
        next_run_at: str | None = None,
        event_name: str | None = None,
        state: dict | None = None,
        memory_context: dict | None = None,
        status: str = "active",
    ):
        """Create a persistent autonomous task definition."""

        if self.database is None:
            return None

        normalized_next_run = next_run_at
        if normalized_next_run is None and interval_seconds is not None:
            normalized_next_run = self._formatDateTime(datetime.utcnow() + timedelta(seconds=int(interval_seconds)))

        cursor = self.database.execute(
            """
            INSERT INTO autonomous_tasks (
                name, task_type, description, status, interval_seconds,
                next_run_at, event_name, state, memory_context
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(name),
                str(task_type),
                str(description or ""),
                str(status),
                int(interval_seconds) if interval_seconds is not None else None,
                normalized_next_run,
                event_name,
                self._encode(state or {}),
                self._encode(memory_context or {}),
            ),
        )
        task_id = getattr(cursor, "lastrowid", None)
        if task_id is None:
            row = self.database.fetchOne("SELECT id FROM autonomous_tasks ORDER BY id DESC LIMIT 1")
            task_id = row.get("id") if row else None

        task = self.getTask(task_id) if task_id is not None else None
        self._emit("autonomous.task.created", {"task": task})
        return task

    def getTask(self, task_id: int | str | None):
        """Return one autonomous task as a dictionary."""

        if self.database is None or task_id is None:
            return None

        row = self.database.fetchOne(
            """
            SELECT id, name, task_type, description, status, interval_seconds,
                   next_run_at, last_run_at, event_name, state, memory_context,
                   created_at, updated_at
            FROM autonomous_tasks
            WHERE id = ?
            """,
            (int(task_id),),
        )
        return self._prepareRow(row)

    def listTasks(self, status: str | None = None):
        """Return all autonomous tasks, optionally filtered by status."""

        if self.database is None:
            return []

        rows = self.database.fetchAll(
            """
            SELECT id, name, task_type, description, status, interval_seconds,
                   next_run_at, last_run_at, event_name, state, memory_context,
                   created_at, updated_at
            FROM autonomous_tasks
            ORDER BY id ASC
            """
        )
        tasks = [self._prepareRow(row) for row in rows]
        if status is not None:
            normalized_status = str(status).lower()
            tasks = [task for task in tasks if str(task.get("status")).lower() == normalized_status]
        return tasks

    def pauseTask(self, task_id: int):
        """Pause an autonomous task so scheduled/event wakeups ignore it."""

        self._updateStatus(task_id, "paused")
        task = self.getTask(task_id)
        self._emit("autonomous.task.paused", {"task": task})
        return task

    def resumeTask(self, task_id: int, next_run_at: str | None = None):
        """Resume a paused task and optionally set its next wakeup time."""

        if self.database is None:
            return None

        task = self.getTask(task_id)
        if task is None:
            return None

        if next_run_at is None and task.get("next_run_at") is None and task.get("interval_seconds") is not None:
            next_run_at = self._formatDateTime(
                datetime.utcnow() + timedelta(seconds=int(task["interval_seconds"]))
            )

        if next_run_at is None:
            self._updateStatus(task_id, "active")
        else:
            self.database.execute(
                """
                UPDATE autonomous_tasks
                SET status = ?, next_run_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                ("active", next_run_at, int(task_id)),
            )

        task = self.getTask(task_id)
        self._emit("autonomous.task.resumed", {"task": task})
        return task

    def updateState(self, task_id: int, state: dict):
        """Persist the latest task-specific state."""

        if self.database is None:
            return None

        self.database.execute(
            """
            UPDATE autonomous_tasks
            SET state = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (self._encode(state), int(task_id)),
        )
        return self.getTask(task_id)

    def wakeDueTasks(self):
        """Run active tasks whose scheduled wakeup time has arrived."""

        now = self._formatDateTime(datetime.utcnow())
        due_tasks = [
            task for task in self.listTasks(status="active")
            if task.get("next_run_at") is not None and str(task["next_run_at"]) <= now
        ]

        for task in due_tasks:
            self.runTask(task["id"], reason="schedule")

        return due_tasks

    def runTask(self, task_id: int, reason: str = "manual", trigger_event: dict | None = None):
        """Dispatch one autonomous task through the task manager or inline."""

        task = self.getTask(task_id)
        if task is None or task.get("status") != "active":
            return None

        payload = self._buildExecutionPayload(task, reason, trigger_event=trigger_event)

        task_manager = getattr(self.context, "taskManager", None)
        threader = getattr(self.context, "threader", None)
        if task_manager is not None and threader is not None:
            background_task = Task(
                name=f"autonomous_{task['id']}_{int(datetime.utcnow().timestamp())}",
                target=self._executeTaskPayload,
                args=(payload,),
            )
            task_manager.submitTask(background_task)
            return background_task

        return self._executeTaskPayload(payload)

    def handleEventWakeup(self, event_name: str, data: dict | None = None):
        """Run active tasks listening for a specific event name."""

        matching = [
            task for task in self.listTasks(status="active")
            if task.get("event_name") == event_name
        ]
        for task in matching:
            self.runTask(
                task["id"],
                reason="event",
                trigger_event={"name": event_name, "data": data or {}},
            )
        return matching

    def _executeTaskPayload(self, payload: dict):
        """Run a task payload through events and an optional registered handler."""

        task = payload["task"]
        task_type = task["task_type"]
        result = None
        error = None

        self._emit("autonomous.task.started", payload)
        try:
            handler = self.handlers.get(task_type)
            if handler is not None:
                result = handler(payload)
            event = self._emit("autonomous.task.wakeup", {**payload, "result": result})
            result = event.data.get("result") if event is not None else result
        except Exception as exc:
            error = str(exc)
            if self.logger:
                self.logger.error(f"Autonomous task failed: {task['id']} ({error})")

        self._recordRun(task, result=result, error=error)
        self._emit(
            "autonomous.task.completed" if error is None else "autonomous.task.failed",
            {**payload, "result": result, "error": error},
        )
        return result

    def _recordRun(self, task: dict, result=None, error: str | None = None):
        """Persist last-run metadata and compute the next scheduled wakeup."""

        if self.database is None:
            return

        now = datetime.utcnow()
        next_run_at = None
        if task.get("interval_seconds") is not None and task.get("status") == "active":
            next_run_at = self._formatDateTime(now + timedelta(seconds=int(task["interval_seconds"])))

        state = dict(task.get("state") or {})
        state["last_result"] = result
        state["last_error"] = error

        self.database.execute(
            """
            UPDATE autonomous_tasks
            SET last_run_at = ?, next_run_at = ?, state = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (self._formatDateTime(now), next_run_at, self._encode(state), int(task["id"])),
        )

    def _buildExecutionPayload(self, task: dict, reason: str, trigger_event: dict | None = None):
        memory = {}
        memory_manager = getattr(self.context, "memoryManager", None)
        if memory_manager is not None and hasattr(memory_manager, "getMemory"):
            memory = memory_manager.getMemory()

        return {
            "task": task,
            "reason": reason,
            "state": dict(task.get("state") or {}),
            "memory_context": dict(task.get("memory_context") or {}),
            "memory": memory,
            "trigger_event": trigger_event,
        }

    def _handleCreateEvent(self, event):
        task = self.createTask(**event.data)
        event.data["task"] = task

    def _handlePauseEvent(self, event):
        event.data["task"] = self.pauseTask(event.data["task_id"])

    def _handleResumeEvent(self, event):
        event.data["task"] = self.resumeTask(
            event.data["task_id"],
            next_run_at=event.data.get("next_run_at"),
        )

    def _handleRunEvent(self, event):
        event.data["result"] = self.runTask(event.data["task_id"], reason=event.data.get("reason", "event"))

    def _updateStatus(self, task_id: int, status: str):
        if self.database is None:
            return

        self.database.execute(
            """
            UPDATE autonomous_tasks
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (str(status), int(task_id)),
        )

    def _emit(self, event_name: str, data: dict):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is None:
            return None
        return event_manager.emit(event_name, data)

    def _prepareRow(self, row):
        if row is None:
            return None
        prepared = dict(row)
        prepared["state"] = self._decode(prepared.get("state"))
        prepared["memory_context"] = self._decode(prepared.get("memory_context"))
        return prepared

    @staticmethod
    def _encode(value: dict):
        return json.dumps(value or {}, sort_keys=True)

    @staticmethod
    def _decode(value):
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _formatDateTime(value: datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
