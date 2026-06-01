"""Unified personal schedule coordinator for Aura."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any

from modules.personalSchedule.handlers.scheduleEventHandler import ScheduleEventHandler
from modules.personalSchedule.models import RecurrenceRule, Reminder, ScheduleItem, ScheduleItemType, ScheduleState, Task, Timer
from modules.personalSchedule.recurrenceManager import RecurrenceManager
from modules.personalSchedule.scheduleActionExecutor import ScheduleActionExecutor
from modules.personalSchedule.scheduleNotificationManager import ScheduleNotificationManager
from modules.personalSchedule.scheduleQueryEngine import ScheduleQueryEngine
from modules.personalSchedule.scheduling.recurrenceEngine import RecurrenceEngine
from modules.personalSchedule.scheduling.reminderScheduler import ReminderScheduler
from modules.personalSchedule.scheduling.scheduleEngine import ScheduleEngine
from modules.personalSchedule.scheduling.timerScheduler import TimerScheduler
from modules.personalSchedule.storage.sqliteScheduleStore import SQLiteScheduleStore


class ScheduleManager:
    """Master coordinator for all time-management surfaces in Aura."""

    def __init__(self, context):
        self.context = context
        self.logger = context.logger.getChild("PersonalSchedule") if getattr(context, "logger", None) else None
        self.enabled = bool(self._getConfigValue("personalScheduleEnabled", True))
        self.allowRecurringSchedules = bool(self._getConfigValue("allowRecurringSchedules", True))
        self.persistScheduleData = bool(self._getConfigValue("persistScheduleData", True))
        self.tickIntervalSeconds = int(self._getConfigValue("scheduleTickIntervalSeconds", 1))
        self.defaultReminderPriority = str(self._getConfigValue("defaultReminderPriority", "NORMAL") or "NORMAL")
        self.databasePath = str(self._getConfigValue("personalSchedule.databasePath", "aura_schedule.sqlite3"))
        self.store = SQLiteScheduleStore(self.databasePath) if self.persistScheduleData else None
        self.scheduleEngine = ScheduleEngine()
        self.recurrenceEngine = RecurrenceEngine()
        self.recurrenceManager = RecurrenceManager()
        self.reminderScheduler = ReminderScheduler()
        self.timerScheduler = TimerScheduler()
        self.notificationManager = ScheduleNotificationManager(context, self)
        self.actionExecutor = ScheduleActionExecutor(self)
        self.queryEngine = ScheduleQueryEngine(self)
        self.eventHandler = ScheduleEventHandler(context, self)
        self._registeredTickName = "personal_schedule_tick"
        self._loaded = False

        self.context.scheduleManager = self
        self.context.personalSchedule = self
        self.context.scheduleNotificationManager = self.notificationManager
        self.context.scheduleQueryEngine = self.queryEngine
        self.context.scheduleActionExecutor = self.actionExecutor

    def initialize(self):
        self._registerTickSchedule()
        self._loaded = True
        return self

    def shutdown(self):
        self.eventHandler.unsubscribe()
        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is not None and hasattr(scheduler, "removeSchedule"):
            try:
                scheduler.removeSchedule(self._registeredTickName)
            except Exception:
                pass
        if self.store is not None:
            self.store.shutdown()

    def refreshContext(self):
        self.enabled = bool(self._getConfigValue("personalScheduleEnabled", self.enabled))
        self.allowRecurringSchedules = bool(self._getConfigValue("allowRecurringSchedules", self.allowRecurringSchedules))
        self.persistScheduleData = bool(self._getConfigValue("persistScheduleData", self.persistScheduleData))
        self.tickIntervalSeconds = int(self._getConfigValue("scheduleTickIntervalSeconds", self.tickIntervalSeconds))
        self.defaultReminderPriority = str(self._getConfigValue("defaultReminderPriority", self.defaultReminderPriority) or self.defaultReminderPriority)
        return self.snapshot()

    def processTick(self, payload: dict[str, Any] | None = None):
        if not self.enabled:
            return {"processed": 0, "triggered": []}
        nowIso = self._now()
        dueItems = self._dueItems(nowIso)
        triggered = []
        for item in dueItems:
            result = self._triggerItem(item, nowIso)
            if result is not None:
                triggered.append(result)
        self._markOverdueTasks(nowIso)
        return {"processed": len(dueItems), "triggered": triggered}

    def saveItem(self, item: ScheduleItem, eventName: str | None = None):
        item.updatedAt = self._now()
        if not item.createdAt:
            item.createdAt = item.updatedAt
        if self.store is not None:
            self.store.upsertItem(item)
        if eventName:
            self._emit(eventName, item.asDict())
        return item

    def createScheduleItem(self, **fields):
        itemType = ScheduleItemType.normalize(fields.get("type"))
        item = ScheduleItem.fromDict(fields)
        item.type = itemType
        if itemType == ScheduleItemType.REMINDER:
            item.dueTime = item.dueTime or item.startTime or item.endTime
            item.priority = str(fields.get("priority") or self.defaultReminderPriority)
        if itemType == ScheduleItemType.TIMER and not item.endTime:
            duration = int(fields.get("durationSeconds") or fields.get("duration_seconds") or item.metadata.get("durationSeconds") or 0)
            item.endTime = self.timerScheduler.endTimeFromDuration(duration)
            item.metadata["durationSeconds"] = duration
        if itemType == ScheduleItemType.TASK and not item.dueTime:
            item.dueTime = item.startTime or fields.get("dueDate") or fields.get("due_date") or ""
        if itemType in {ScheduleItemType.BILL, ScheduleItemType.DEADLINE} and not item.dueTime:
            item.dueTime = item.startTime or fields.get("dueDate") or fields.get("due_date") or ""
        if item.recurrenceRule and not self.allowRecurringSchedules:
            item.recurrenceRule = None
        return self.saveItem(item, eventName="schedule.item.created")

    def updateScheduleItem(self, itemId: str, **fields):
        item = self.getScheduleItem(itemId)
        if item is None:
            raise KeyError(f"Unknown schedule item: {itemId}")
        updated = ScheduleItem.fromDict({**item.asDict(), **fields, "itemId": item.itemId})
        updated.createdAt = item.createdAt
        updated.updatedAt = self._now()
        if self.store is not None:
            self.store.upsertItem(updated)
        self._emit("schedule.item.updated", updated.asDict())
        return updated

    def deleteScheduleItem(self, itemId: str):
        item = self.getScheduleItem(itemId)
        if self.store is not None:
            self.store.deleteItem(itemId)
        if item is not None:
            self._emit("schedule.item.deleted", item.asDict())
        return {"itemId": str(itemId)}

    def getScheduleItem(self, itemId: str):
        if self.store is None:
            return None
        return self.store.getItem(itemId)

    def listScheduleItems(self, itemType: ScheduleItemType | str | None = None, state: ScheduleState | str | None = None):
        if self.store is None:
            return []
        items = self.store.listItems()
        if itemType is not None:
            itemType = ScheduleItemType.normalize(itemType)
            items = [item for item in items if item.type == itemType]
        if state is not None:
            state = ScheduleState.normalize(state)
            items = [item for item in items if item.state == state]
        return items

    def searchSchedule(self, query: str, limit: int = 20):
        if self.store is None:
            return []
        return self.store.searchItems(query, limit=limit)

    def getTodaysSchedule(self):
        return self.queryEngine.getTodaysSchedule()

    def getUpcomingSchedule(self, limit: int = 10):
        return self.queryEngine.getUpcomingSchedule(limit=limit)

    def getUpcomingReminders(self, limit: int = 10):
        return self.queryEngine.getUpcomingReminders(limit=limit)

    def getOverdueTasks(self, limit: int = 10):
        return self.queryEngine.getOverdueTasks(limit=limit)

    def buildDayView(self, day: str):
        items = self._itemsForDay(day)
        return {
            "day": str(day),
            "summary": f"{len(items)} item(s)",
            "items": [item.asDict() for item in items],
            "events": [item.asDict() for item in items if item.type == ScheduleItemType.EVENT or item.type == ScheduleItemType.MEETING],
            "meetings": [item.asDict() for item in items if item.type == ScheduleItemType.MEETING],
            "tasks": [item.asDict() for item in items if item.type == ScheduleItemType.TASK],
            "reminders": [item.asDict() for item in items if item.type == ScheduleItemType.REMINDER],
            "timers": [item.asDict() for item in items if item.type == ScheduleItemType.TIMER],
            "bills": [item.asDict() for item in items if item.type == ScheduleItemType.BILL],
            "routines": [item.asDict() for item in items if item.type == ScheduleItemType.ROUTINE],
            "deadlines": [item.asDict() for item in items if item.type == ScheduleItemType.DEADLINE],
        }

    def buildWeekView(self, day: str):
        start = datetime.fromisoformat(f"{str(day)[:10]}T00:00:00")
        days = []
        for offset in range(7):
            current = (start + timedelta(days=offset)).date().isoformat()
            days.append({"day": current, "items": [item.asDict() for item in self._itemsForDay(current)]})
        return {
            "week_start": start.date().isoformat(),
            "week_end": (start + timedelta(days=6)).date().isoformat(),
            "days": days,
            "events": [item.asDict() for item in self.listScheduleItems() if item.type in {ScheduleItemType.EVENT, ScheduleItemType.MEETING}],
            "tasks": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.TASK)],
            "reminders": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.REMINDER)],
            "timers": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.TIMER)],
            "bills": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.BILL)],
            "routines": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.ROUTINE)],
            "deadlines": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.DEADLINE)],
        }

    def buildMonthView(self, month_value: str):
        start = datetime.fromisoformat(f"{str(month_value)[:10]}T00:00:00")
        days = []
        for offset in range(31):
            current = (start + timedelta(days=offset)).date().isoformat()
            days.append({"day": current, "items": [item.asDict() for item in self._itemsForDay(current)]})
        return {
            "month": start.strftime("%Y-%m"),
            "days": days,
            "events": [item.asDict() for item in self.listScheduleItems() if item.type in {ScheduleItemType.EVENT, ScheduleItemType.MEETING}],
            "tasks": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.TASK)],
            "reminders": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.REMINDER)],
            "timers": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.TIMER)],
            "bills": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.BILL)],
            "routines": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.ROUTINE)],
            "deadlines": [item.asDict() for item in self.listScheduleItems(itemType=ScheduleItemType.DEADLINE)],
        }

    def createReminder(self, title: str, dueTime: str, description: str = "", priority: str | None = None, tags=None, recurrenceRule=None, metadata=None, source: str = "assistant", requiresAcknowledgement: bool = False, **fields):
        normalizedRule = recurrenceRule
        if normalizedRule is not None and not isinstance(normalizedRule, RecurrenceRule):
            normalizedRule = RecurrenceRule.fromDict(normalizedRule)
        item = Reminder(
            title=title,
            description=description,
            dueTime=dueTime,
            priority=priority or self.defaultReminderPriority,
            tags=list(tags or []),
            recurrenceRule=normalizedRule,
            metadata=dict(metadata or {}),
        )
        created = self.createScheduleItem(
            title=item.title,
            description=item.description,
            type=ScheduleItemType.REMINDER,
            dueTime=item.dueTime,
            priority=item.priority,
            tags=item.tags,
            recurrenceRule=item.recurrenceRule.asDict() if item.recurrenceRule else None,
            metadata=item.metadata,
            source=source,
            requiresAcknowledgement=requiresAcknowledgement,
            **fields,
        )
        return created

    def createTask(self, title: str, dueDate: str = "", description: str = "", priority: str = "NORMAL", tags=None, repeatRule=None, metadata=None, source: str = "assistant", requiresAcknowledgement: bool = False, **fields):
        normalizedRule = repeatRule
        if normalizedRule is not None and not isinstance(normalizedRule, RecurrenceRule):
            normalizedRule = RecurrenceRule.fromDict(normalizedRule)
        item = Task(
            title=title,
            description=description,
            dueDate=dueDate,
            priority=priority,
            completed=False,
            tags=list(tags or []),
            repeatRule=normalizedRule or {},
            metadata=dict(metadata or {}),
        )
        created = self.createScheduleItem(
            title=item.title,
            description=item.description,
            type=ScheduleItemType.TASK,
            dueTime=item.dueDate,
            priority=item.priority,
            tags=item.tags,
            recurrenceRule=item.repeatRule.asDict() if isinstance(item.repeatRule, RecurrenceRule) else item.repeatRule,
            metadata=item.metadata,
            source=source,
            requiresAcknowledgement=requiresAcknowledgement,
            **fields,
        )
        return created

    def createTimer(self, title: str = "", durationSeconds: int = 0, description: str = "", priority: str = "NORMAL", tags=None, metadata=None, source: str = "assistant", requiresAcknowledgement: bool = False, **fields):
        item = Timer(title=title or "Timer", durationSeconds=int(durationSeconds or 0), remainingSeconds=int(durationSeconds or 0), metadata=dict(metadata or {}))
        item.metadata["durationSeconds"] = int(durationSeconds or 0)
        return self.createScheduleItem(
            title=item.title,
            description=description,
            type=ScheduleItemType.TIMER,
            endTime=self.timerScheduler.endTimeFromDuration(item.durationSeconds),
            priority=priority,
            tags=list(tags or []),
            metadata=item.metadata,
            source=source,
            requiresAcknowledgement=requiresAcknowledgement,
            **fields,
        )

    def completeTask(self, itemId: str):
        item = self.getScheduleItem(itemId)
        if item is None:
            raise KeyError(f"Unknown schedule item: {itemId}")
        item.state = ScheduleState.COMPLETED
        return self.saveItem(item, eventName="schedule.item.updated")

    def pauseTimer(self, itemId: str):
        item = self.getScheduleItem(itemId)
        if item is None:
            raise KeyError(f"Unknown schedule item: {itemId}")
        item.state = ScheduleState.SNOOZED
        return self.saveItem(item, eventName="schedule.item.updated")

    def resumeTimer(self, itemId: str):
        item = self.getScheduleItem(itemId)
        if item is None:
            raise KeyError(f"Unknown schedule item: {itemId}")
        item.state = ScheduleState.ACTIVE
        return self.saveItem(item, eventName="schedule.item.updated")

    def completeTimer(self, itemId: str):
        item = self.getScheduleItem(itemId)
        if item is None:
            raise KeyError(f"Unknown schedule item: {itemId}")
        item.state = ScheduleState.COMPLETED
        self.saveItem(item, eventName="schedule.item.updated")
        self.notificationManager.notifyItem(item, "timer.completed", f"Timer finished: {item.title}", priority=item.priority)
        self._emit("timer.completed", item.asDict())
        return item

    def handleAction(self, actionName: str, **fields):
        return self.actionExecutor.execute(actionName, **fields)

    def snapshot(self) -> dict[str, Any]:
        items = self.listScheduleItems()
        return {
            "available": True,
            "enabled": self.enabled,
            "persistScheduleData": self.persistScheduleData,
            "allowRecurringSchedules": self.allowRecurringSchedules,
            "tickIntervalSeconds": self.tickIntervalSeconds,
            "defaultReminderPriority": self.defaultReminderPriority,
            "storedCount": len(items),
            "items": [item.asDict() for item in items[:20]],
            "today": self.getTodaysSchedule(),
            "upcoming": self.getUpcomingSchedule(),
            "overdueTasks": self.getOverdueTasks(),
        }

    def _registerTickSchedule(self):
        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is None:
            return
        if scheduler.getSchedule(self._registeredTickName) is not None:
            return
        try:
            from core.threading.scheduler.schedule import Schedule

            scheduler.addSchedule(Schedule(name=self._registeredTickName, target=self._emitTick, interval=max(1.0, float(self.tickIntervalSeconds))))
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Personal schedule tick not registered: {error}")

    def _emitTick(self):
        self._emit("schedule.tick", {"timestamp": self._now(), "source": "scheduler"})

    def _dueItems(self, nowIso: str):
        if self.store is None:
            return []
        return self.store.listDueItems(nowIso)

    def _markOverdueTasks(self, nowIso: str):
        overdue = self.store.listOverdueItems(nowIso) if self.store is not None else []
        for item in overdue:
            if item.type == ScheduleItemType.TASK and item.state != ScheduleState.COMPLETED:
                item.state = ScheduleState.OVERDUE
                self.saveItem(item, eventName="schedule.item.updated")
                self._emit("task.overdue", item.asDict())

    def _triggerItem(self, item: ScheduleItem, nowIso: str):
        itemType = item.type
        if itemType == ScheduleItemType.TIMER:
            item.state = ScheduleState.COMPLETED
            self.saveItem(item, eventName="schedule.item.updated")
            self.notificationManager.notifyItem(item, "timer.completed", f"Timer finished: {item.title}", priority=item.priority)
            self._emit("timer.completed", item.asDict())
            self._emit("schedule.item.triggered", item.asDict())
            return item.asDict()
        if itemType in {ScheduleItemType.REMINDER, ScheduleItemType.EVENT, ScheduleItemType.MEETING, ScheduleItemType.ROUTINE}:
            item.state = ScheduleState.COMPLETED
            self.saveItem(item, eventName="schedule.item.updated")
            self.notificationManager.notifyItem(item, "schedule.item.triggered", f"{item.title} is due now.", priority=item.priority)
            self._emit("schedule.item.triggered", item.asDict())
            self._rescheduleIfRecurring(item, nowIso)
            return item.asDict()
        if itemType in {ScheduleItemType.BILL, ScheduleItemType.DEADLINE, ScheduleItemType.TASK}:
            if item.state != ScheduleState.COMPLETED:
                item.state = ScheduleState.OVERDUE
                self.saveItem(item, eventName="schedule.item.updated")
                self.notificationManager.notifyItem(item, "schedule.item.triggered", f"{item.title} is overdue.", priority="HIGH" if itemType != ScheduleItemType.TASK else item.priority)
                self._emit("schedule.item.triggered", item.asDict())
                self._rescheduleIfRecurring(item, nowIso)
                return item.asDict()
        return None

    def _rescheduleIfRecurring(self, item: ScheduleItem, nowIso: str):
        if not self.allowRecurringSchedules or item.recurrenceRule is None:
            return
        nextOccurrence = self.recurrenceManager.nextOccurrence(item.recurrenceRule, nowIso, item.startTime or item.dueTime or item.createdAt)
        if not nextOccurrence:
            return
        item.startTime = item.startTime or nextOccurrence
        if item.type in {ScheduleItemType.REMINDER, ScheduleItemType.BILL, ScheduleItemType.DEADLINE, ScheduleItemType.TASK}:
            item.dueTime = nextOccurrence
        else:
            item.startTime = nextOccurrence
        item.state = ScheduleState.PENDING
        self.saveItem(item, eventName="schedule.item.updated")

    def _itemsForDay(self, day: str):
        target = str(day or "")[:10]
        items = []
        for item in self.listScheduleItems():
            candidate = self._itemDate(item)
            if candidate == target:
                items.append(item)
        return items

    @staticmethod
    def _itemDate(item: ScheduleItem) -> str:
        return str(item.startTime or item.dueTime or item.endTime or item.createdAt)[:10]

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Personal schedule event emission failed for {eventName}: {error}")
        return None

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    @staticmethod
    def _now():
        return datetime.utcnow().isoformat(timespec="seconds")
