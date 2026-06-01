"""Recurring task scheduling helpers."""

from __future__ import annotations

from datetime import datetime


class RecurringScheduler:
    """Compute and register recurring task wakeups."""

    def __init__(self, taskManager=None):
        self.taskManager = taskManager

    def scheduleNext(self, task):
        if self.taskManager is None:
            return None
        return self.taskManager._rescheduleRecurring(task)
