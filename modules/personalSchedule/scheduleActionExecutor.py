"""Action execution for Aura's personal schedule hub."""

from __future__ import annotations


class ScheduleActionExecutor:
    """Dispatch schedule actions to the correct manager method."""

    def __init__(self, manager):
        self.manager = manager

    def execute(self, actionName: str, **fields):
        actionName = str(actionName or "")
        mapping = {
            "schedule.createItem": self.manager.createScheduleItem,
            "schedule.updateItem": self.manager.updateScheduleItem,
            "schedule.deleteItem": self.manager.deleteScheduleItem,
            "schedule.getToday": self.manager.getTodaysSchedule,
            "schedule.getUpcoming": self.manager.getUpcomingSchedule,
            "schedule.createReminder": self.manager.createReminder,
            "schedule.createTask": self.manager.createTask,
            "schedule.completeTask": self.manager.completeTask,
            "schedule.createTimer": self.manager.createTimer,
            "schedule.pauseTimer": self.manager.pauseTimer,
            "schedule.resumeTimer": self.manager.resumeTimer,
            "schedule.completeTimer": self.manager.completeTimer,
        }
        handler = mapping.get(actionName)
        if handler is None:
            raise ValueError(f"Unsupported schedule action: {actionName}")
        return handler(**fields)
