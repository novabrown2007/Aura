"""Regression coverage for Aura's lightweight async task system."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.tasks import AuraTask, BackgroundJobManager, RecurringTaskManager, RetryPolicy, TaskManager, TaskState
from core.threading.events.eventManager import EventManager
from core.threading.tasks.task import Task
from core.threading.threadingManager import ThreadingManager


class _TaskConfig:
    """Tiny config stub for task system tests."""

    def __init__(self, path: str):
        self._data = {
            "task": {
                "taskSystemEnabled": True,
                "taskPersistenceEnabled": True,
                "backgroundJobsEnabled": True,
                "maxConcurrentTasks": 2,
                "taskSchedulerTickIntervalMs": 20,
                "defaultRetryAttempts": 2,
                "defaultRetryDelaySeconds": 0,
                "databasePath": path,
            }
        }

    def get(self, key, default=None):
        value = self._data
        for part in str(key).split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value


class AsyncTaskTests(unittest.TestCase):
    """Validate delayed, recurring, retrying, and persisted task behavior."""

    def makeContext(self, path: str):
        context = SimpleNamespace()
        context.logger = None
        context.observability = None
        context.config = _TaskConfig(path)
        context.eventManager = EventManager(context)
        context.threader = ThreadingManager(context)
        context.executionManager = None
        context.taskManager = None
        return context

    def waitForIdle(self, context, timeout: float = 1.0):
        """Wait until legacy compatibility tasks are cleared."""

        deadline = time.time() + timeout
        while time.time() < deadline:
            if not context.taskManager.listTasks():
                return
            time.sleep(0.01)
        self.fail("Task manager did not become idle.")

    def waitForThreadStopped(self, context, name, timeout: float = 1.0):
        """Wait until a managed thread stops."""

        deadline = time.time() + timeout
        while time.time() < deadline:
            thread = context.threader.getThread(name)
            if thread is None or not thread.is_alive():
                return
            time.sleep(0.01)
        self.fail(f"Thread did not stop: {name}")

    def test_legacy_submit_task_runs_in_managed_thread(self):
        """Legacy Task submissions should still execute and clean up correctly."""

        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(str(Path(tempDir) / "tasks.sqlite3"))
            context.taskManager = TaskManager(context)
            calls = []

            context.taskManager.submitTask(Task(name="repeatable", target=lambda: calls.append("done")))
            self.waitForIdle(context)
            self.waitForThreadStopped(context, "task_repeatable")

            self.assertEqual(calls, ["done"])
            self.assertEqual(context.taskManager.listTasks(), [])
            self.assertEqual(len(context.taskManager.completedTasks()), 1)
            context.taskManager.shutdown()

    def test_delayed_task_is_persisted_and_reloaded(self):
        """Delayed tasks should survive a manager restart."""

        with tempfile.TemporaryDirectory() as tempDir:
            taskPath = str(Path(tempDir) / "tasks.sqlite3")
            context = self.makeContext(taskPath)
            manager = TaskManager(context)
            task = manager.scheduleDelayed("reminder", delaySeconds=60, executionContext={"note": "call john"})
            self.assertEqual(task.state, TaskState.SCHEDULED)
            self.assertGreaterEqual(len(manager.queue.listTasks()), 1)
            manager.shutdown()

            reloadedContext = self.makeContext(taskPath)
            reloaded = TaskManager(reloadedContext)
            loadedTasks = reloaded.queue.listTasks()

            self.assertEqual(len(loadedTasks), 1)
            self.assertEqual(loadedTasks[0].taskName, "reminder")
            self.assertEqual(loadedTasks[0].executionContext["note"], "call john")
            reloaded.shutdown()

    def test_failed_task_reschedules_once_with_retry_policy(self):
        """A failing task should be retried through the shared retry manager."""

        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(str(Path(tempDir) / "tasks.sqlite3"))
            manager = TaskManager(context)
            attempts = []

            def target():
                attempts.append(len(attempts))
                if len(attempts) == 1:
                    raise RuntimeError("temporary failure")
                return "ok"

            task = AuraTask(
                taskName="retryable",
                executionContext={"target": target},
                retryPolicy=RetryPolicy(maxRetries=2, retryDelaySeconds=0, backoffMultiplier=1),
            )

            result1 = manager._runQueuedTask(task)
            self.assertEqual(result1.status, TaskState.FAILED)
            self.assertEqual(task.state, TaskState.RETRYING)
            self.assertEqual(len(manager.queue.listTasks()), 1)

            retryTask = manager.queue.popDue()[0]
            result2 = manager._runQueuedTask(retryTask)
            self.assertEqual(result2.status, TaskState.COMPLETED)
            self.assertEqual(attempts, [0, 1])
            self.assertEqual(retryTask.state, TaskState.COMPLETED)
            manager.shutdown()

    def test_recurring_task_is_rescheduled_after_completion(self):
        """Recurring tasks should schedule their next run automatically."""

        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(str(Path(tempDir) / "tasks.sqlite3"))
            manager = TaskManager(context)
            calls = []
            recurring = manager.recurringTaskManager.createRecurringTask("poll", 60, metadata={"source": "monitor"})
            task = AuraTask(
                taskName="poll",
                executionContext={"target": lambda: calls.append("tick"), "recurringTask": recurring.asDict()},
                recurringTask=recurring,
            )

            result = manager._runQueuedTask(task)
            self.assertEqual(result.status, TaskState.COMPLETED)
            self.assertEqual(calls, ["tick"])
            self.assertEqual(len(manager.queue.listTasks()), 1)
            self.assertEqual(manager.queue.listTasks()[0].taskName, "poll")
            manager.shutdown()

    def test_background_job_registration_creates_recurring_job(self):
        """Background jobs should register recurring tasks through the manager."""

        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(str(Path(tempDir) / "tasks.sqlite3"))
            manager = TaskManager(context)

            job = manager.backgroundJobManager.registerJob(
                "weather_refresh",
                30,
                target=lambda: "refreshed",
                executionContext={"source": "weather"},
            )

            self.assertTrue(job.enabled)
            self.assertEqual(job.taskName, "weather_refresh")
            self.assertGreaterEqual(len(manager.registry.listRecurringTasks()), 1)
            manager.shutdown()

    def test_cancel_task_removes_it_from_the_queue(self):
        """Cancellation should stop a scheduled task without executing it."""

        with tempfile.TemporaryDirectory() as tempDir:
            context = self.makeContext(str(Path(tempDir) / "tasks.sqlite3"))
            manager = TaskManager(context)
            task = manager.scheduleDelayed("cancel_me", delaySeconds=60, executionContext={"note": "later"})

            cancelled = manager.cancelTask(task)

            self.assertEqual(cancelled.state, TaskState.CANCELLED)
            self.assertEqual(len(manager.queue.listTasks()), 0)
            manager.shutdown()


if __name__ == "__main__":
    unittest.main()
