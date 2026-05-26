"""Assistant ecosystem simulator for Aura."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..debugging.assistantConsole import AssistantConsole
from ..debugging.eventTracer import EventTracer
from ..debugging.intentDebugger import IntentDebugger
from ..debugging.sessionDebugger import SessionDebugger
from ..mock.mockNotifications import MockNotifications
from ..mock.mockUser import MockUser
from ..mock.mockVoiceInput import MockVoiceInput
from ..harnesses.intentTester import IntentTester


class AssistantSimulator:
    """Simulate assistant sessions, notifications, and intent workflows."""

    def __init__(self, context=None, bridgeClient=None, voiceManager=None, tracer=None, console=None):
        self.context = context
        self.bridgeClient = bridgeClient or getattr(context, "bridgeClient", None)
        self.voiceManager = voiceManager or getattr(context, "voiceManager", None)
        self.tracer = tracer or EventTracer(context)
        self.console = console or AssistantConsole(context, self.tracer)
        self.sessionDebugger = SessionDebugger(context)
        self.intentDebugger = IntentDebugger(context)
        self.intentTester = IntentTester(context, self.tracer, self.intentDebugger)
        self.mockUser = MockUser()

    def createSession(self, interface: str = "desktop", sessionId: str | None = None):
        """Create a simulated assistant session."""

        session = self.sessionDebugger.createSession(interface=interface, sessionId=sessionId or uuid4().hex)
        self.tracer.traceSession(session.sessionId, {"interface": session.interface, "state": session.state})
        self.console.displaySession(f"{session.sessionId} ({session.interface})")
        return session

    def subscribe(self, categories: list[str], interface: str = "desktop", sessionId: str = ""):
        """Simulate a bridge subscription request."""

        payload = {"categories": list(categories), "interface": interface, "sessionId": sessionId}
        self.tracer.traceProtocol("subscription", payload)
        self.console.displaySubscription(f"subscribe -> {categories}")
        if self.bridgeClient is not None and hasattr(self.bridgeClient, "subscriptionManager"):
            return self.bridgeClient.subscriptionManager.subscribe(categories=categories, interface=interface, sessionId=sessionId)
        return payload

    def simulateTextConversation(self, text: str, sessionId: str = "", interface: str = "desktop"):
        """Simulate a typed assistant conversation."""

        user = self.mockUser.typedInput(text)
        self.tracer.trace("input", "text", user)
        self.console.displayVoice(user["text"])
        return self._routeTextToAssistant(user["text"], sessionId=sessionId, interface=interface)

    def simulateVoiceConversation(self, text: str, sessionId: str = "", speak: bool = False, interface: str = "voice"):
        """Simulate a voice assistant conversation using mock input."""

        voiceInput = MockVoiceInput.create(text).toDict()
        self.tracer.trace("input", "voice", voiceInput)
        self.console.displayVoice(f"\"{voiceInput['text']}\"")
        return self._simulateVoiceWorkflow(voiceInput["text"], sessionId=sessionId, interface=interface, speak=speak)

    def simulateNotificationWorkflow(self, notification: dict[str, Any], sessionId: str = ""):
        """Simulate a notification-driven assistant reaction."""

        payload = self._normalizePayload(notification)
        self.tracer.traceNotification(payload)
        self.console.displayNotification(f"{payload.get('event') or payload.get('category')} -> {payload.get('location') or payload.get('deviceId') or payload.get('name') or ''}".strip())
        self._updateBridgeState(payload)
        response = self._buildNotificationResponse(payload)
        self.console.displayResponse(response)
        self.tracer.traceResponse(response, {"source": "notification", "sessionId": sessionId})
        return {"notification": payload, "response": response, "sessionId": sessionId}

    def simulateAssistantContext(self, contextData: dict[str, Any], sessionId: str = "", interface: str = "desktop"):
        """Simulate an assistant.context update."""

        payload = self._normalizePayload(contextData)
        payload.setdefault("sessionId", sessionId)
        payload.setdefault("interface", interface)
        self.tracer.traceProtocol("assistant.context", payload)
        self.console.displayAnalysis(f"context -> {payload.get('sessionId') or 'session'}")
        if self.bridgeClient is not None and hasattr(self.bridgeClient, "stateCache"):
            stateCache = getattr(self.bridgeClient, "stateCache", None)
            if stateCache is not None:
                stateCache.updateMessage({"category": "assistant.context", "data": payload, "context": {"sessionId": sessionId, "interface": interface}})
        return payload

    def simulateStreamWorkflow(self, stream: dict[str, Any], sessionId: str = ""):
        """Simulate a stream availability workflow."""

        payload = self._normalizePayload(stream)
        self.tracer.traceProtocol("stream.available", payload)
        self.console.displayStream(f"{payload.get('streamId') or 'stream'}")
        if self.bridgeClient is not None:
            stateCache = getattr(self.bridgeClient, "stateCache", None)
            if stateCache is not None:
                stateCache.updateMessage(
                    {
                        "category": "assistant.stream.available",
                        "data": payload,
                        "context": {"sessionId": sessionId},
                    }
                )
        return {"stream": payload, "sessionId": sessionId}

    def syncSession(self, sessionId: str, interface: str = "desktop"):
        """Synchronize session state into the debuggers and bridge cache."""

        session = self.sessionDebugger.updateSession(sessionId, interface=interface, state="active")
        self.tracer.traceSession(session.sessionId, {"interface": session.interface, "state": session.state})
        self.console.displaySession(f"{session.sessionId} ({session.interface})")
        return session

    def emitMockNotification(self, notification: dict[str, Any]):
        """Emit one mocked notification payload."""

        return self.simulateNotificationWorkflow(notification)

    def snapshot(self):
        """Return a debugging snapshot for the simulated assistant ecosystem."""

        return {
            "console": self.console.getLines(),
            "events": self.tracer.getEvents(),
            "sessions": self.sessionDebugger.snapshot(),
            "intents": self.intentDebugger.snapshot(),
        }

    def _routeTextToAssistant(self, text: str, sessionId: str = "", interface: str = "desktop"):
        """Send text into the existing assistant pipeline."""

        intent = self._buildIntent(text)
        self.intentDebugger.recordIntent(intent["intent"], intent.get("confidence", 0.0), intent.get("arguments", {}))
        valid, message = self.intentTester.validateIntent(intent)
        if not valid:
            self.intentDebugger.recordValidationFailure(intent.get("intent", ""), message, intent.get("arguments", {}))
            self.console.displayIntent(f"invalid -> {message}")
            return {"success": False, "error": message, "intent": intent}

        payload = self.intentTester.buildBridgeRequest(intent, sessionId=sessionId, interface=interface)
        self.console.displayIntent(str(payload["data"]["intent"]))
        self.console.displayBridge("assistant.intent sent")
        self.tracer.traceProtocol("assistant.intent", payload)

        response = self._submitIntent(payload)
        assistantResponse = self._extractAssistantResponse(response, text)
        self.intentDebugger.recordExecutionResponse(intent["intent"], assistantResponse)
        self.console.displayResponse(assistantResponse)
        self.tracer.traceResponse(assistantResponse, {"intent": intent["intent"], "sessionId": sessionId})
        return {
            "success": True,
            "intent": intent,
            "request": payload,
            "response": response,
            "assistantResponse": assistantResponse,
        }

    def _simulateVoiceWorkflow(self, text: str, sessionId: str = "", interface: str = "voice", speak: bool = False):
        """Simulate the full voice-to-assistant workflow."""

        result = self._routeTextToAssistant(text, sessionId=sessionId, interface=interface)
        if speak and self.voiceManager is not None and hasattr(self.voiceManager, "speakResponse"):
            try:
                self.voiceManager.speakResponse(result.get("assistantResponse", ""))
            except Exception as error:
                if getattr(self.context, "logger", None):
                    self.context.logger.warning(f"Simulated voice playback failed: {error}")
        return result

    def _buildIntent(self, text: str):
        """Build a deterministic assistant intent from text."""

        text = str(text or "").strip()
        normalized = text.lower()
        if "light" in normalized and ("off" in normalized or "disable" in normalized):
            intent = "lights.turnOff"
        elif "light" in normalized and ("on" in normalized or "enable" in normalized):
            intent = "lights.turnOn"
        elif "brightness" in normalized or "%" in normalized:
            intent = "lights.setBrightness"
        elif "camera" in normalized and "stream" in normalized:
            intent = "camera.startStream"
        else:
            intent = "conversation.reply"
        arguments = self._extractArguments(text, intent)
        return {"intent": intent, "confidence": 0.92, "arguments": arguments}

    def _extractArguments(self, text: str, intent: str):
        """Extract simple deterministic arguments from text."""

        arguments = {}
        lower = text.lower()
        if "bedroom" in lower:
            arguments["room"] = "bedroom"
        if intent == "lights.setBrightness":
            digits = "".join(char for char in text if char.isdigit())
            if digits:
                arguments["brightness"] = int(digits)
        if intent.startswith("camera"):
            arguments["device_id"] = "camera-bedroom-01"
        return self.intentTester.normalizeArguments(arguments)

    def _submitIntent(self, payload: dict[str, Any]):
        """Submit a request through the bridge client or a simulated bridge."""

        if self.bridgeClient is not None and hasattr(self.bridgeClient, "submitIntent"):
            try:
                return self.bridgeClient.submitIntent(payload["data"], sessionId=payload["context"]["sessionId"], interface=payload["context"]["interface"])
            except Exception as error:
                if getattr(self.context, "logger", None):
                    self.context.logger.warning(f"Bridge submit failed in simulator: {error}")
        return {
            "ok": True,
            "message": {
                "category": "assistant.response",
                "data": {
                    "requestId": uuid4().hex,
                    "success": True,
                    "response": "Command executed successfully",
                },
            },
        }

    def _extractAssistantResponse(self, response, text: str):
        """Normalize any bridge or mock response into assistant text."""

        if isinstance(response, dict):
            message = response.get("message")
            if isinstance(message, dict):
                data = message.get("data") if isinstance(message.get("data"), dict) else message
                response_text = data.get("response") or data.get("message") or data.get("status")
                if response_text:
                    return str(response_text)
            if isinstance(response.get("data"), dict):
                data = response["data"]
                response_text = data.get("response") or data.get("message") or data.get("status")
                if response_text:
                    return str(response_text)
            messages = response.get("messages")
            if isinstance(messages, list):
                for item in messages:
                    if isinstance(item, dict):
                        data = item.get("data")
                        if isinstance(data, dict):
                            response_text = data.get("response") or data.get("message") or data.get("status")
                            if response_text:
                                return str(response_text)
        return "Command executed successfully"

    def _updateBridgeState(self, payload: dict[str, Any]):
        """Update any connected bridge cache with the mock notification."""

        if self.bridgeClient is None:
            return
        stateCache = getattr(self.bridgeClient, "stateCache", None)
        if stateCache is None:
            return
        message = {
            "category": "assistant.notification",
            "data": payload,
            "context": {"sessionId": ""},
        }
        stateCache.updateMessage(message)

    def _buildNotificationResponse(self, payload: dict[str, Any]):
        """Build a deterministic assistant notification response."""

        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        event = str(payload.get("event") or payload.get("category") or "notification")
        if isinstance(data, dict):
            event = str(data.get("event") or event)
            payload = data
        if event == "motionDetected":
            return "Motion detected. I have noted it."
        if event == "deviceOffline":
            return "A device reported offline."
        if event == "automationCompleted":
            return "Automation completed successfully."
        if event == "streamAvailable":
            return "A stream is available."
        return f"Notification received: {event}"

    @staticmethod
    def _normalizePayload(payload: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize protocol envelopes and flat payload dictionaries."""

        normalized = dict(payload or {})
        data = normalized.get("data")
        if isinstance(data, dict):
            merged = dict(data)
            merged.setdefault("category", str(normalized.get("category") or ""))
            merged.setdefault("context", dict(normalized.get("context") or {}))
            return merged
        return normalized
