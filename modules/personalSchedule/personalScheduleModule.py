"""Aura's unified personal schedule capability module."""

from __future__ import annotations

from core.modules.base import AuraModule, ModuleMetadata, ModuleSubscription
from core.modules.modulePermissions import ModulePermissions
from core.tools.tool import Tool
from modules.personalSchedule.actions.reminderActions import REMINDER_ACTIONS
from modules.personalSchedule.actions.scheduleActions import SCHEDULE_ACTIONS
from modules.personalSchedule.actions.taskActions import TASK_ACTIONS
from modules.personalSchedule.actions.timerActions import TIMER_ACTIONS
from modules.personalSchedule.intents.reminderIntents import REMINDER_INTENTS
from modules.personalSchedule.intents.scheduleIntents import SCHEDULE_INTENTS
from modules.personalSchedule.intents.taskIntents import TASK_INTENTS
from modules.personalSchedule.intents.timerIntents import TIMER_INTENTS
from modules.personalSchedule.scheduleManager import ScheduleManager


MODULE_METADATA = ModuleMetadata(
    name="personalSchedule",
    version="1.0.0",
    author="Aura",
    description="Unified personal schedule hub for events, reminders, tasks, deadlines, bills, routines, and timers.",
    permissions=("database:read", "database:write"),
    capabilities=(
        "schedule.read",
        "schedule.write",
        "schedule.modify",
        "schedule.notifications",
        "schedule.recurring",
        "schedule.tasks",
        "schedule.reminders",
        "schedule.timers",
    ),
)


class PersonalScheduleModule(AuraModule):
    """Module entrypoint for Aura's unified schedule system."""

    metadata = MODULE_METADATA

    def __init__(self, context=None):
        super().__init__()
        self.manager: ScheduleManager | None = None
        self._tickRegistered = False
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        super().initialize(context)
        self.manager = ScheduleManager(context).initialize()
        self.permissions = ModulePermissions(capabilityPermissions=tuple(self.metadata.permissions))
        self._logStartup("personalSchedule module started.")
        return self

    def shutdown(self):
        if self.manager is not None:
            self.manager.shutdown()

    def getIntents(self):
        return list((*SCHEDULE_INTENTS, *REMINDER_INTENTS, *TASK_INTENTS, *TIMER_INTENTS))

    def getActions(self):
        return list((*SCHEDULE_ACTIONS, *REMINDER_ACTIONS, *TASK_ACTIONS, *TIMER_ACTIONS))

    def getSubscriptions(self):
        return [
            ModuleSubscription(eventName="schedule.tick", handler="handleEvent"),
            ModuleSubscription(eventName="system.started", handler="handleEvent"),
            ModuleSubscription(eventName="conversation.started", handler="handleEvent"),
            ModuleSubscription(eventName="notification.acknowledged", handler="handleEvent"),
        ]

    def getPermissions(self):
        return self.permissions

    def getTools(self):
        return [
            Tool(
                name="schedule.createItem",
                description="Create a unified schedule item.",
                parameters={
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "type": {"type": "string"},
                    "startTime": {"type": "string"},
                    "endTime": {"type": "string"},
                    "dueTime": {"type": "string"},
                    "priority": {"type": "string"},
                },
                requiredParameters=("title",),
                module="personalSchedule",
                method="createScheduleItem",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("schedule.write",),
                riskLevel="LOW",
            ),
            Tool(
                name="schedule.createReminder",
                description="Create a reminder.",
                parameters={"title": {"type": "string"}, "dueTime": {"type": "string"}},
                requiredParameters=("title", "dueTime"),
                module="personalSchedule",
                method="createReminder",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("schedule.reminders",),
                riskLevel="LOW",
            ),
            Tool(
                name="schedule.createTask",
                description="Create a task.",
                parameters={"title": {"type": "string"}, "dueDate": {"type": "string"}},
                requiredParameters=("title",),
                module="personalSchedule",
                method="createTask",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("schedule.tasks",),
                riskLevel="LOW",
            ),
            Tool(
                name="schedule.createTimer",
                description="Create a timer.",
                parameters={"title": {"type": "string"}, "durationSeconds": {"type": "integer"}},
                requiredParameters=("durationSeconds",),
                module="personalSchedule",
                method="createTimer",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("schedule.timers",),
                riskLevel="LOW",
            ),
            Tool(
                name="schedule.completeTimer",
                description="Mark a timer as completed.",
                parameters={"itemId": {"type": "string"}},
                requiredParameters=("itemId",),
                module="personalSchedule",
                method="completeTimer",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("schedule.timers",),
                riskLevel="LOW",
            ),
            Tool(
                name="schedule.getToday",
                description="Summarize today's unified schedule.",
                parameters={},
                module="personalSchedule",
                method="getTodaysSchedule",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("schedule.read",),
                riskLevel="LOW",
            ),
            Tool(
                name="schedule.getUpcoming",
                description="Return upcoming schedule items.",
                parameters={"limit": {"type": "integer"}},
                module="personalSchedule",
                method="getUpcomingSchedule",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("schedule.read",),
                riskLevel="LOW",
            ),
        ]

    def handleEvent(self, event):
        if self.manager is None:
            return None
        return self.manager.eventHandler.handleEvent(event)

    def handleIntent(self, intent):
        intentName = getattr(intent, "name", intent)
        arguments = dict(getattr(intent, "arguments", {}) or {})
        if self.manager is None:
            raise RuntimeError("personalSchedule manager is not available.")
        return self.manager.handleAction(intentName, **arguments)

    def snapshot(self):
        if self.manager is None:
            return {"available": False, "enabled": False}
        return self.manager.snapshot()

    def listScheduleItems(self, *args, **kwargs):
        return self.manager.listScheduleItems(*args, **kwargs)

    def createScheduleItem(self, **fields):
        return self.manager.createScheduleItem(**fields)

    def updateScheduleItem(self, itemId: str, **fields):
        return self.manager.updateScheduleItem(itemId, **fields)

    def deleteScheduleItem(self, itemId: str):
        return self.manager.deleteScheduleItem(itemId)

    def createReminder(self, **fields):
        return self.manager.createReminder(**fields)

    def createTask(self, **fields):
        return self.manager.createTask(**fields)

    def completeTask(self, itemId: str):
        return self.manager.completeTask(itemId)

    def createTimer(self, **fields):
        return self.manager.createTimer(**fields)

    def pauseTimer(self, itemId: str):
        return self.manager.pauseTimer(itemId)

    def resumeTimer(self, itemId: str):
        return self.manager.resumeTimer(itemId)

    def completeTimer(self, itemId: str):
        return self.manager.completeTimer(itemId)

    def buildDayView(self, day: str):
        return self.manager.buildDayView(day)

    def buildWeekView(self, day: str):
        return self.manager.buildWeekView(day)

    def buildMonthView(self, month_value: str):
        return self.manager.buildMonthView(month_value)

    def searchSchedule(self, query: str, limit: int = 20):
        return self.manager.searchSchedule(query, limit=limit)

    def getTodaysSchedule(self):
        return self.manager.getTodaysSchedule()

    def getUpcomingSchedule(self, limit: int = 10):
        return self.manager.getUpcomingSchedule(limit=limit)

    def getOverdueTasks(self, limit: int = 10):
        return self.manager.getOverdueTasks(limit=limit)

def createModule(context=None):
    """Create the unified personal schedule module."""

    return PersonalScheduleModule(context)
