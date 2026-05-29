"""Central assistant attention-management coordinator."""

from __future__ import annotations

from threading import RLock
from typing import Any

from assistant.notifications.deliveryStrategyManager import DeliveryStrategyManager
from assistant.notifications.escalationManager import EscalationManager
from assistant.notifications.handlers.notificationEventHandler import NotificationEventHandler
from assistant.notifications.interruptionManager import InterruptionManager
from assistant.notifications.models.notification import Notification
from assistant.notifications.models.notificationPriority import NotificationPriority
from assistant.notifications.notificationHistory import NotificationHistory
from assistant.notifications.notificationPriorityEngine import NotificationPriorityEngine
from assistant.notifications.notificationQueue import NotificationQueue
from assistant.notifications.notificationRouter import NotificationRouter
from assistant.notifications.notificationSuppression import NotificationSuppression


class NotificationManager:
    """Coordinate notification prioritization, routing, escalation, and history."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Notifications") if context and getattr(context, "logger", None) else None
        self.enabled = bool(self._getConfigValue("notifications.notificationsEnabled", True))
        self.allowVoiceInterruptions = bool(self._getConfigValue("notifications.allowVoiceInterruptions", True))
        self.criticalAlwaysInterrupt = bool(self._getConfigValue("notifications.criticalNotificationsAlwaysInterrupt", True))
        self.cooldownSeconds = int(self._getConfigValue("notifications.notificationCooldownSeconds", 30))
        self.maxQueuedNotifications = int(self._getConfigValue("notifications.maxQueuedNotifications", 50))
        self.quietHoursEnabled = bool(self._getConfigValue("notifications.quietHoursEnabled", False))

        self.priorityEngine = NotificationPriorityEngine(context)
        self.deliveryStrategyManager = DeliveryStrategyManager()
        self.suppression = NotificationSuppression(cooldownSeconds=self.cooldownSeconds)
        self.queue = NotificationQueue(maxSize=self.maxQueuedNotifications)
        self.history = NotificationHistory()
        self.escalationManager = EscalationManager()
        self.interruptionManager = InterruptionManager(context)
        self.router = NotificationRouter(context)
        self.eventHandler = NotificationEventHandler(context, self)
        self._lock = RLock()
        self._activeNotifications: dict[str, Notification] = {}
        self._deliveredNotifications: dict[str, Notification] = {}
        self._suppressedNotifications: list[dict[str, Any]] = []
        self._escalationHistory: list[dict[str, Any]] = []
        self._currentAlertId = ""
        self.initialized = False

        if self.context is not None:
            self.initialize(self.context)

    def initialize(self, context=None):
        """Attach the manager to the runtime context and subscribe to events."""

        if context is not None:
            self.context = context
        if self.context is None:
            return self

        self.context.notificationManager = self
        self.context.notificationPriorityEngine = self.priorityEngine
        self.context.notificationDeliveryStrategyManager = self.deliveryStrategyManager
        self.context.notificationInterruptionManager = self.interruptionManager
        self.context.notificationHistory = self.history
        self.context.notificationQueue = self.queue
        self.context.notificationSuppression = self.suppression
        self.context.notificationEscalationManager = self.escalationManager
        self.context.notificationRouter = self.router

        if self.eventHandler is not None:
            self.eventHandler.subscribe()

        self._registerEscalationSchedule()
        self.initialized = True
        if self.logger:
            self.logger.info("Notification manager initialized.")
        return self

    def shutdown(self):
        """Unsubscribe and clear transient attention state."""

        if self.eventHandler is not None:
            self.eventHandler.unsubscribe()
        with self._lock:
            self._activeNotifications.clear()
            self._deliveredNotifications.clear()
            self._currentAlertId = ""
        self.queue.clear()
        if self.logger:
            self.logger.info("Notification manager shut down.")

    def handleEvent(self, event):
        """Convert one runtime event into a notification when appropriate."""

        eventName = getattr(event, "name", "")
        payload = dict(getattr(event, "data", {}) or {})
        if eventName == "notifications.create":
            return self._handleExternalCreate(payload, event)
        if eventName == "interruption.completed":
            return self._handleInterruptionCompleted(payload)
        if eventName in {"conversation.started", "conversation.active"}:
            return self._refreshContextState()
        return self.createNotification(payload, eventName=eventName, sourceEvent=event)

    def createNotification(self, payload: dict[str, Any], eventName: str = "", sourceEvent=None):
        """Create, classify, and queue a notification."""

        if not self.enabled:
            return None

        notificationData, route = self.priorityEngine.buildNotification(payload, eventName=eventName, runtimeContext=self.context)
        notification = Notification.fromDict(notificationData)

        suppressed, reason = self.suppression.shouldSuppress(notification.asDict(), self._contextSnapshot())
        if suppressed:
            self._recordSuppressed(notification, reason or "suppressed")
            return None

        if self._isQueueOverloaded(notification):
            self._recordSuppressed(notification, "queue_overflow")
            return None

        notificationId = self._persistNotification(notification)
        if notificationId:
            notification.notificationId = str(notificationId)
        with self._lock:
            self._activeNotifications[notification.notificationId or notification.title or notification.message] = notification
        self.history.record("notification.created", notification.asDict(), {"eventName": eventName})
        self._emit("notification.created", notification.asDict())

        if route.queue:
            overflow = self.queue.enqueue(notification.asDict())
            if overflow is not None and self.logger:
                self.logger.warning("Notification queue overflowed; dropped lowest-priority item.")
            self._processQueue()
        else:
            self._deliver(notification, route)
        self.escalationManager.register(notification.asDict())
        return notification

    def acknowledge(self, notificationId: str, source: str = "ui"):
        """Acknowledge one active notification."""

        with self._lock:
            notification = self._activeNotifications.pop(str(notificationId), None)
            if notification is None:
                notification = self._deliveredNotifications.get(str(notificationId))
        if notification is None:
            return False
        self.escalationManager.acknowledge(str(notificationId))
        self.history.record("notification.acknowledged", notification.asDict(), {"source": source})
        self._emit("notification.acknowledged", notification.asDict())
        return True

    def poll(self):
        """Process queued items and re-alert overdue escalations."""

        self._processQueue()
        for overdue in self.escalationManager.poll():
            notification = self._deliveredNotifications.get(str(overdue.get("notificationId")))
            if notification is None:
                continue
            self._escalationHistory.append(dict(overdue))
            self.history.record("notification.escalated", notification.asDict(), dict(overdue))
            self._emit("notification.escalated", notification.asDict())
            route = self.priorityEngine.classifyRoute(notification.asDict(), self.context)
            route.interrupt = True
            route.voice = True
            route.ui = True
            self._deliver(notification, route, escalated=True)

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable notification state snapshot."""

        with self._lock:
            active = [notification.asDict() for notification in self._activeNotifications.values()]
            delivered = [notification.asDict() for notification in self._deliveredNotifications.values()]
        return {
            "available": True,
            "enabled": self.enabled,
            "activeNotifications": active,
            "deliveredNotifications": delivered,
            "queuedNotifications": self.queue.snapshot(),
            "suppressedNotifications": list(self._suppressedNotifications),
            "escalationState": self.escalationManager.snapshot(),
            "history": self.history.snapshot(),
            "allowVoiceInterruptions": self.allowVoiceInterruptions,
            "criticalAlwaysInterrupt": self.criticalAlwaysInterrupt,
            "cooldownSeconds": self.cooldownSeconds,
            "maxQueuedNotifications": self.maxQueuedNotifications,
            "quietHoursEnabled": self.quietHoursEnabled,
        }

    def _deliver(self, notification: Notification, route, escalated: bool = False):
        """Route one notification to the appropriate delivery surfaces."""

        result = self.router.route(notification, route, self.priorityEngine._buildNotificationContext(self.context))
        if result.get("interrupted"):
            self.history.record("notification.interrupted", notification.asDict(), {"escalated": escalated})
            self._emit("notification.interrupted", notification.asDict())
        with self._lock:
            self._deliveredNotifications[notification.notificationId or notification.title or notification.message] = notification
            self._currentAlertId = notification.notificationId or self._currentAlertId
            if notification.notificationId:
                self._activeNotifications.pop(notification.notificationId, None)
        self.history.record("notification.delivered", notification.asDict(), result)
        self._emit("notification.delivered", notification.asDict())
        return result

    def _processQueue(self):
        """Drain queued notifications in priority order."""

        while True:
            item = self.queue.dequeue()
            if item is None:
                break
            notification = Notification.fromDict(item)
            route = self.priorityEngine.classifyRoute(notification.asDict(), self.context)
            self._deliver(notification, route)

    def _recordSuppressed(self, notification: Notification, reason: str):
        payload = notification.asDict()
        payload["reason"] = reason
        with self._lock:
            self._suppressedNotifications.append(payload)
        self.history.record("notification.suppressed", notification.asDict(), {"reason": reason})
        self._emit("notification.suppressed", payload)

    def _handleExternalCreate(self, payload: dict[str, Any], event):
        """Allow existing notification persistence events to flow through the attention layer."""

        notificationId = payload.get("notification_id") or payload.get("notificationId")
        if notificationId is not None:
            return notificationId
        return self._persistNotification(Notification.fromDict(payload))

    def _handleInterruptionCompleted(self, payload: dict[str, Any]):
        """Acknowledge the current alert when a stop/cancel command succeeds."""

        request = payload.get("request") or {}
        phrase = str(request.get("phrase") or "").strip().lower()
        if phrase in {"stop", "cancel", "nevermind", "never mind", "pause"} and self._currentAlertId:
            self.acknowledge(self._currentAlertId, source="interruption")
            self._currentAlertId = ""
        return None

    def _refreshContextState(self):
        """Refresh cached attention state from the runtime context."""

        if self.context is None:
            return None
        self.enabled = bool(self._getConfigValue("notifications.notificationsEnabled", self.enabled))
        self.allowVoiceInterruptions = bool(self._getConfigValue("notifications.allowVoiceInterruptions", self.allowVoiceInterruptions))
        self.criticalAlwaysInterrupt = bool(self._getConfigValue("notifications.criticalNotificationsAlwaysInterrupt", self.criticalAlwaysInterrupt))
        self.cooldownSeconds = int(self._getConfigValue("notifications.notificationCooldownSeconds", self.cooldownSeconds))
        self.suppression.cooldownSeconds = self.cooldownSeconds
        self.maxQueuedNotifications = int(self._getConfigValue("notifications.maxQueuedNotifications", self.maxQueuedNotifications))
        self.queue.maxSize = self.maxQueuedNotifications
        self.quietHoursEnabled = bool(self._getConfigValue("notifications.quietHoursEnabled", self.quietHoursEnabled))
        self.priorityEngine.context = self.context
        return None

    def _persistNotification(self, notification: Notification):
        """Persist the notification using the existing notification storage module when available."""

        notifications = getattr(self.context, "notifications", None)
        if notifications is not None and hasattr(notifications, "createNotification"):
            try:
                return notifications.createNotification(
                    source_module=notification.source,
                    title=notification.title,
                    content=notification.message,
                    timestamp=notification.timestamp,
                )
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Notification persistence failed: {error}")
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is not None:
            try:
                event = eventManager.emit(
                    "notifications.create",
                    {
                        "source_module": notification.source,
                        "title": notification.title,
                        "content": notification.message,
                        "timestamp": notification.timestamp,
                    },
                )
                if getattr(event, "data", None) and event.data.get("notification_id") is not None:
                    return event.data.get("notification_id")
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Notification event persistence failed: {error}")
        return notification.notificationId or None

    def _contextSnapshot(self):
        return self.priorityEngine._buildNotificationContext(self.context).asDict()

    def _isQueueOverloaded(self, notification: Notification):
        if self.maxQueuedNotifications <= 0:
            return False
        if self.queue.snapshot()["count"] < self.maxQueuedNotifications:
            return False
        return NotificationPriority.normalize(notification.priority) not in {NotificationPriority.HIGH, NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY}

    def _registerEscalationSchedule(self):
        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is None or scheduler.getSchedule("notification_poll") is not None:
            return
        try:
            from core.threading.scheduler.schedule import Schedule

            scheduler.addSchedule(Schedule(name="notification_poll", target=self.poll, interval=5.0))
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Notification escalation schedule not registered: {error}")

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Notification event emission failed for {eventName}: {error}")
        return None

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
