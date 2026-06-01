"""Event bus bridge for Aura's Windows desktop overlay."""

from __future__ import annotations


class OverlayEventHandler:
    """Subscribe to voice, notification, and provider events."""

    eventNames = (
        "wakeword.detected",
        "voice.capture.started",
        "voice.capture.finished",
        "stt.processing.started",
        "response.generated",
        "tts.started",
        "tts.finished",
        "notification.created",
        "notification.delivered",
        "notification.interrupted",
        "provider.connected",
        "provider.disconnected",
        "assistant.shutdown.requested",
    )

    def __init__(self, context=None, overlayManager=None):
        self.context = context
        self.overlayManager = overlayManager
        self._subscribed = False
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.OverlayEvents") if logger else None

    def subscribe(self):
        if self._subscribed:
            return
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        for eventName in self.eventNames:
            try:
                eventManager.subscribe(eventName, self.handleEvent)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Overlay event subscription failed for {eventName}: {error}")
        self._subscribed = True

    def unsubscribe(self):
        if not self._subscribed:
            return
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        for eventName in self.eventNames:
            try:
                eventManager.unsubscribe(eventName, self.handleEvent)
            except Exception:
                pass
        self._subscribed = False

    def handleEvent(self, event):
        payload = getattr(event, "data", {}) or {}
        name = getattr(event, "name", "")
        self._dispatch(name, payload)

    def _dispatch(self, name: str, payload: dict):
        manager = self.overlayManager
        if manager is None:
            return
        if name == "wakeword.detected":
            manager.updateAssistant("LISTENING", payload.get("phrase", "Wake word detected"))
            manager.updateMic("LISTENING", activity=True, confidence=float(payload.get("confidence", 0.0) or 0.0))
            manager.showBubble()
        elif name == "voice.capture.started":
            manager.updateAssistant("LISTENING", "Recording")
            manager.updateMic("LISTENING", activity=True, confidence=float(payload.get("confidence", 0.0) or 0.0))
        elif name == "voice.capture.finished":
            manager.updateAssistant("PROCESSING", "Finalizing speech")
            manager.updateMic("PROCESSING", activity=False, confidence=float(payload.get("confidence", 0.0) or 0.0))
            manager.setProcessing(True, "Processing speech")
        elif name == "stt.processing.started":
            manager.updateAssistant("PROCESSING", "Transcribing")
            manager.setProcessing(True, "Transcribing")
        elif name == "response.generated":
            manager.updateAssistant("RESPONDING", "Responding")
            manager.setProcessing(False)
        elif name == "tts.started":
            manager.updateAssistant("RESPONDING", "Speaking")
            manager.updateMic("RESPONDING", activity=False)
        elif name == "tts.finished":
            manager.updateAssistant("IDLE", "")
            manager.updateMic("IDLE", activity=False)
            manager.setProcessing(False)
        elif name == "notification.created":
            manager.updateAssistant("NOTIFYING", str(payload.get("title") or payload.get("message") or "Notification"))
            manager.showNotification(payload)
        elif name == "notification.delivered":
            manager.showNotification(payload)
        elif name == "notification.interrupted":
            manager.updateAssistant("NOTIFYING", "Notification interrupted")
            manager.showNotification(payload)
        elif name == "provider.connected":
            manager.updateConnection(True, str(payload.get("provider") or ""))
        elif name == "provider.disconnected":
            manager.updateConnection(False, str(payload.get("provider") or ""))
        elif name == "assistant.shutdown.requested":
            manager.markEvent(name)
