"""Workflow simulation helpers for assistant ecosystem testing."""

from __future__ import annotations

from typing import Any


class WorkflowSimulator:
    """Simulate canonical assistant ecosystem workflows."""

    def __init__(self, context=None, assistantSimulator=None):
        self.context = context
        self.assistantSimulator = assistantSimulator
        self.logger = context.logger.getChild("Testing.WorkflowSimulator") if context and getattr(context, "logger", None) else None

    def simulateVoiceInputWorkflow(self, text: str, sessionId: str = "", speak: bool = False):
        """Simulate the voice input to bridge response path."""

        if self.assistantSimulator is not None:
            return self.assistantSimulator.simulateVoiceConversation(text, sessionId=sessionId, speak=speak)
        if self.logger:
            self.logger.debug("No assistant simulator available; echoing voice input.")
        return {"input": text, "assistantResponse": text}

    def simulateTextConversation(self, text: str, sessionId: str = "", interface: str = "desktop"):
        """Compatibility alias for text conversation workflows."""

        return self.simulateVoiceInputWorkflow(text, sessionId=sessionId)

    def simulateNotificationWorkflow(self, notification: dict[str, Any], sessionId: str = ""):
        """Simulate a notification arriving and producing an assistant response."""

        if self.assistantSimulator is not None:
            return self.assistantSimulator.simulateNotificationWorkflow(notification, sessionId=sessionId)
        return {"notification": dict(notification), "response": "Notification received."}

    def simulateSessionSync(self, sessionId: str, interface: str = "desktop"):
        """Simulate session synchronization."""

        if self.assistantSimulator is not None:
            return self.assistantSimulator.syncSession(sessionId=sessionId, interface=interface)
        return {"sessionId": sessionId, "interface": interface}

    def syncSession(self, sessionId: str, interface: str = "desktop"):
        """Compatibility alias for session sync workflows."""

        return self.simulateSessionSync(sessionId=sessionId, interface=interface)

    def simulateStreamRequest(self, streamId: str, endpoint: str = "rtsp://localhost/stream"):
        """Simulate a stream request workflow."""

        payload = {
            "streamId": streamId,
            "streamType": "rtsp",
            "endpoint": endpoint,
        }
        if self.assistantSimulator is not None:
            return self.assistantSimulator.simulateStreamWorkflow(payload)
        return payload

    def simulateStreamWorkflow(self, stream: dict[str, Any], sessionId: str = ""):
        """Compatibility alias for stream availability workflows."""

        if isinstance(stream, dict) and "streamId" in stream:
            payload = dict(stream)
        else:
            payload = {
                "streamId": str(stream.get("streamId") if isinstance(stream, dict) else "stream"),
                "endpoint": str(stream.get("endpoint") if isinstance(stream, dict) else "rtsp://localhost/stream"),
            }
        return self.simulateStreamRequest(
            streamId=str(payload.get("streamId") or "stream"),
            endpoint=str(payload.get("endpoint") or "rtsp://localhost/stream"),
        )

    def simulateEndToEnd(self, text: str, notification: dict[str, Any] | None = None, stream: dict[str, Any] | None = None, sessionId: str = "", speak: bool = False):
        """Simulate the full assistant workflow set used in integration tests."""

        results = {
            "voice": self.simulateVoiceInputWorkflow(text, sessionId=sessionId, speak=speak),
        }
        if notification is not None:
            results["notification"] = self.simulateNotificationWorkflow(notification, sessionId=sessionId)
        if stream is not None:
            results["stream"] = self.simulateStreamRequest(
                streamId=str(stream.get("streamId") or "stream"),
                endpoint=str(stream.get("endpoint") or "rtsp://localhost/stream"),
            )
        return results
