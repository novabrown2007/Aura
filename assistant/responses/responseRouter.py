"""Route structured responses to the appropriate Aura interfaces."""

from __future__ import annotations

from assistant.notifications.models import Notification, NotificationCategory, NotificationDeliveryMode, NotificationPriority


class ResponseRouter:
    """Deliver response surfaces to voice, UI, notifications, and actions."""

    def __init__(self, context=None, formatter=None):
        self.context = context
        self.formatter = formatter
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses.Router") if logger else None

    def route(self, response):
        """Deliver one structured response packet."""

        deliveryResults = {"voice": None, "ui": None, "notifications": [], "actions": []}
        spokenText = self.formatter.formatSpokenText(response) if self.formatter is not None else getattr(response, "spokenText", "")
        uiText = self.formatter.formatUiText(response) if self.formatter is not None else getattr(response, "uiText", "")

        if spokenText and self._configEnabled("responses.spokenResponseEnabled", True):
            deliveryResults["voice"] = self._deliverVoice(spokenText)
        if uiText and self._configEnabled("responses.uiResponseEnabled", True):
            deliveryResults["ui"] = self._deliverUi(uiText)
        for notification in getattr(response, "notifications", []) or []:
            deliveryResults["notifications"].append(self._deliverNotification(notification))
        for action in getattr(response, "actions", []) or []:
            deliveryResults["actions"].append(self._deliverAction(action))
        try:
            response.metadata.deliveryResults = deliveryResults
        except Exception:
            pass
        return deliveryResults

    def _deliverVoice(self, text: str):
        voice = getattr(self.context, "voiceManager", None)
        if voice is None or not hasattr(voice, "speakResponse"):
            return {"available": False, "text": text}
        try:
            result = voice.speakResponse(text)
            return {"available": True, "result": result}
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice delivery failed: {error}")
            return {"available": False, "error": str(error)}

    def _deliverUi(self, text: str):
        overlay = getattr(self.context, "desktopOverlayManager", None)
        if overlay is None:
            return {"available": False, "text": text}
        try:
            overlay.updateAssistant("RESPONDING", text)
            overlay.showBubble()
            return {"available": True}
        except Exception as error:
            if self.logger:
                self.logger.warning(f"UI delivery failed: {error}")
        return {"available": False, "error": str(error)}

    def _deliverNotification(self, notification):
        manager = getattr(self.context, "notificationManager", None)
        payload = notification.asDict() if hasattr(notification, "asDict") else dict(notification or {})
        if manager is None:
            return {"available": False, "notification": payload}
        try:
            result = manager.createNotification(
                {
                    "notificationId": payload.get("notificationId", ""),
                    "title": payload.get("title", ""),
                    "message": payload.get("message", ""),
                    "priority": payload.get("priority", NotificationPriority.NORMAL.value),
                    "category": payload.get("category", NotificationCategory.SYSTEM.value),
                    "deliveryMode": payload.get("deliveryMode", NotificationDeliveryMode.UI_ONLY.value),
                    "persistent": payload.get("persistent", False),
                    "requiresAcknowledgement": payload.get("requiresAcknowledgement", False),
                    "interruptAllowed": payload.get("interruptAllowed", False),
                    "metadata": payload.get("metadata", {}),
                    "source": "response",
                },
                eventName="response.notification",
            )
            return {"available": True, "result": result.asDict() if hasattr(result, "asDict") else result}
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Notification delivery failed: {error}")
            return {"available": False, "error": str(error), "notification": payload}

    def _deliverAction(self, action):
        payload = action.asDict() if hasattr(action, "asDict") else dict(action or {})
        actionName = str(payload.get("target") or payload.get("actionName") or "")
        if not actionName:
            return {"available": False, "error": "Missing action target.", "action": payload}
        if not payload.get("requiresExecution", True):
            return {"available": True, "skipped": True, "action": payload}

        executor = getattr(self.context, "toolExecutor", None)
        if executor is None:
            eventManager = getattr(self.context, "eventManager", None)
            if eventManager is not None:
                try:
                    eventManager.emit("response.action.requested", payload)
                except Exception:
                    pass
            return {"available": False, "error": "Tool executor unavailable.", "action": payload}

        try:
            result = executor.executeToolCall(actionName, payload.get("arguments") or {}, offlineMode=bool(getattr(getattr(self.context, "llmManager", None), "offlineMode", False)))
            return {"available": True, "result": result}
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Action delivery failed: {error}")
            return {"available": False, "error": str(error), "action": payload}

    def _configEnabled(self, key: str, default: bool = True) -> bool:
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
