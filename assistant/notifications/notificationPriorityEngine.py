"""Notification priority classification engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from assistant.notifications.models.notificationCategory import NotificationCategory
from assistant.notifications.models.notificationContext import NotificationContext
from assistant.notifications.models.notificationDeliveryMode import NotificationDeliveryMode
from assistant.notifications.models.notificationPriority import NotificationPriority
from assistant.notifications.rules.notificationRules import NotificationRules


class NotificationPriorityEngine:
    """Classify notification priority and delivery context."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Notifications.Priority") if logger else None

    def buildNotification(self, payload: dict[str, Any], eventName: str = "", runtimeContext=None):
        """Build a normalized notification record."""

        payload = dict(payload or {})
        priority = NotificationPriority.normalize(payload.get("priority") or self.classifyPriority(eventName, payload, runtimeContext))
        category = NotificationCategory.normalize(payload.get("category") or self.classifyCategory(eventName, payload))
        notification = payload.copy()
        notification.setdefault("notificationId", str(payload.get("notificationId") or payload.get("notification_id") or ""))
        notification["title"] = str(payload.get("title") or payload.get("name") or payload.get("message") or "")
        notification["message"] = str(payload.get("message") or payload.get("content") or payload.get("title") or "")
        notification["priority"] = priority.value
        notification["category"] = category.value
        notification.setdefault("timestamp", payload.get("timestamp") or self._now())
        notification.setdefault("source", payload.get("source") or payload.get("source_module") or eventName)
        notification.setdefault("metadata", dict(payload.get("metadata") or {}))
        notification.setdefault("requiresAcknowledgement", priority in {NotificationPriority.HIGH, NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY})
        notification.setdefault("interruptAllowed", priority in {NotificationPriority.HIGH, NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY})
        notification.setdefault("persistent", priority != NotificationPriority.LOW)
        route = self.classifyRoute(notification, runtimeContext)
        notification["deliveryMode"] = route.deliveryMode.value
        return notification, route

    def classifyPriority(self, eventName: str, payload: dict[str, Any], runtimeContext=None) -> NotificationPriority:
        """Classify the urgency of a notification."""

        text = f"{eventName} {payload.get('title', '')} {payload.get('message', '')}".lower()
        if any(term in text for term in ("confirmed fire", "medical emergency", "panic")):
            return NotificationPriority.EMERGENCY
        if any(term in text for term in ("smoke detected", "fire", "water leak", "security breach", "gas leak")):
            return NotificationPriority.CRITICAL
        if any(term in text for term in ("motion detected", "door opened", "unexpected activity", "motion downstairs")):
            hour = self._hourFromContext(runtimeContext, payload)
            if hour is not None and (hour >= 23 or hour < 6):
                return NotificationPriority.CRITICAL
            return NotificationPriority.HIGH
        if any(term in text for term in ("timer completed", "email received", "calendar reminder", "reminder")):
            return NotificationPriority.NORMAL
        if any(term in text for term in ("disconnected", "weather", "stopped", "update")):
            return NotificationPriority.LOW
        return NotificationPriority.NORMAL

    def classifyCategory(self, eventName: str, payload: dict[str, Any]) -> NotificationCategory:
        """Classify the notification category."""

        category = NotificationRules.categoryFromEvent(eventName, payload)
        if category != NotificationCategory.SYSTEM:
            return category
        text = f"{eventName} {payload.get('title', '')} {payload.get('message', '')}".lower()
        if any(term in text for term in ("motion", "door", "smoke", "security", "leak")):
            return NotificationCategory.SECURITY
        if "timer" in text or "reminder" in text:
            return NotificationCategory.REMINDER
        if "calendar" in text or "event" in text:
            return NotificationCategory.CALENDAR
        if "email" in text:
            return NotificationCategory.EMAIL
        if "spotify" in text or "music" in text:
            return NotificationCategory.MEDIA
        if "light" in text or "home" in text:
            return NotificationCategory.SMART_HOME
        if "automation" in text:
            return NotificationCategory.AUTOMATION
        return NotificationCategory.SYSTEM

    def classifyRoute(self, notification: dict[str, Any], runtimeContext=None):
        """Classify the best delivery route for the notification."""

        notificationContext = self._buildNotificationContext(runtimeContext)
        routeManager = getattr(self.context, "notificationDeliveryStrategyManager", None)
        if routeManager is None:
            from assistant.notifications.deliveryStrategyManager import DeliveryStrategyManager

            routeManager = DeliveryStrategyManager()
        return routeManager.chooseRoute(self._toNotification(notification), notificationContext)

    def _buildNotificationContext(self, runtimeContext=None) -> NotificationContext:
        """Collect the current assistant runtime context."""

        runtimeContext = runtimeContext or self.context
        conversation = getattr(runtimeContext, "conversationManager", None)
        conversationSnapshot = conversation.snapshot() if conversation is not None and hasattr(conversation, "snapshot") else {}
        voiceManager = getattr(runtimeContext, "voiceManager", None)
        voiceSpeaking = bool(getattr(voiceManager, "speechQueue", None) and getattr(voiceManager.speechQueue, "_processing", False))
        tts = getattr(runtimeContext, "textToSpeech", None)
        speaking = bool(getattr(tts, "_cancelEvent", None) is not None and getattr(tts, "lastResult", None) and getattr(tts.lastResult, "audioPath", ""))
        quietHoursEnabled = bool(self._getConfigValue(runtimeContext, "notifications.quietHoursEnabled", False))
        quietHoursActive = bool(self._getConfigValue(runtimeContext, "notifications.quietHoursActive", False))
        interfaceType = str(getattr(runtimeContext, "interfaceType", "") or "desktop")
        if bool(self._getConfigValue(runtimeContext, "voice.pushToTalk.enabled", False)):
            interfaceType = "voice"
        return NotificationContext(
            interfaceType=interfaceType,
            conversationActive=bool(conversationSnapshot.get("activeTopic") or conversationSnapshot.get("pendingClarification", {}).get("active")),
            activeTopic=str((conversationSnapshot.get("activeTopic") or {}).get("name") or ""),
            activeEntity=str((conversationSnapshot.get("activeEntity") or {}).get("name") or ""),
            voiceSpeaking=bool(voiceSpeaking or speaking),
            speechQueueBusy=bool(getattr(getattr(runtimeContext, "speechQueue", None), "_processing", False)),
            quietHoursEnabled=quietHoursEnabled,
            quietHoursActive=quietHoursActive,
            allowVoiceInterruptions=bool(self._getConfigValue(runtimeContext, "notifications.allowVoiceInterruptions", True)),
            criticalAlwaysInterrupt=bool(self._getConfigValue(runtimeContext, "notifications.criticalNotificationsAlwaysInterrupt", True)),
            userActivityState=str(self._getConfigValue(runtimeContext, "context.activityState", "idle") or "idle"),
            timestamp=self._now(),
        )

    def _toNotification(self, payload: dict[str, Any]):
        from assistant.notifications.models.notification import Notification

        return Notification.fromDict(payload)

    @staticmethod
    def _getConfigValue(runtimeContext, key: str, default=None):
        config = getattr(runtimeContext, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    @staticmethod
    def _hourFromContext(runtimeContext, payload: dict[str, Any]) -> int | None:
        timestamp = payload.get("timestamp")
        if isinstance(timestamp, str) and len(timestamp) >= 13:
            try:
                return datetime.fromisoformat(timestamp.replace(" ", "T")).hour
            except Exception:
                pass
        config = getattr(runtimeContext, "config", None)
        if config is not None and hasattr(config, "get"):
            nowValue = config.get("runtime.currentHour", None)
            if nowValue is not None:
                try:
                    return int(nowValue)
                except Exception:
                    return None
        return None

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
