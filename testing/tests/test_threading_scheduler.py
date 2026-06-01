"""Regression tests for Aura task and scheduler lifecycle behavior."""

import time
import unittest
from types import SimpleNamespace

from core.threading.scheduler.schedule import Schedule
from core.threading.scheduler.scheduler import Scheduler
from core.threading.tasks.task import Task
from core.threading.tasks.taskManager import TaskManager
from core.threading.threadingManager import ThreadingManager


class ThreadingSchedulerTests(unittest.TestCase):
    """Validate recurring scheduled tasks do not collide with completed work."""

    def makeContext(self):
        """Build the minimal runtime context needed by threading services."""

        context = SimpleNamespace(logger=None, eventManager=None, observability=None)
        context.threader = ThreadingManager(context)
        context.taskManager = TaskManager(context)
        return context

    def waitForTaskManagerIdle(self, context, timeout=1.0):
        """Wait until task cleanup has removed all active task records."""

        deadline = time.time() + timeout
        while time.time() < deadline:
            if not context.taskManager.listTasks():
                return
            time.sleep(0.01)
        self.fail("Task manager did not become idle.")

    def waitForThreadStopped(self, context, name, timeout=1.0):
        """Wait until a managed thread with the supplied name is no longer alive."""

        deadline = time.time() + timeout
        while time.time() < deadline:
            thread = context.threader.getThread(name)
            if thread is None or not thread.is_alive():
                return
            time.sleep(0.01)
        self.fail(f"Thread did not stop: {name}")

    def test_completed_task_name_can_be_submitted_again(self):
        """Completed tasks should not block later work with the same name."""

        context = self.makeContext()
        calls = []

        context.taskManager.submitTask(Task(name="repeatable", target=lambda: calls.append("first")))
        self.waitForTaskManagerIdle(context)
        self.waitForThreadStopped(context, "task_repeatable")

        context.taskManager.submitTask(Task(name="repeatable", target=lambda: calls.append("second")))
        self.waitForTaskManagerIdle(context)

        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(context.taskManager.listTasks(), [])
        self.assertEqual(len(context.taskManager.completedTasks()), 2)

    def test_scheduler_can_run_repeating_schedule_more_than_once(self):
        """A repeating schedule should not crash on the second due tick."""

        context = self.makeContext()
        scheduler = Scheduler(context)
        calls = []
        scheduler.addSchedule(
            Schedule(
                name="personal_schedule_tick",
                target=lambda: calls.append("poll"),
                interval=0.0,
            )
        )

        scheduler._tick()
        self.waitForTaskManagerIdle(context)
        self.waitForThreadStopped(context, "task_schedule_personal_schedule_tick")
        scheduler._tick()
        self.waitForTaskManagerIdle(context)

        self.assertEqual(calls, ["poll", "poll"])


if __name__ == "__main__":
    unittest.main()
