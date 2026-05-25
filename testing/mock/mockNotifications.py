"""Mock assistant notification payloads for testing."""

from __future__ import annotations


class MockNotifications:
    """Generate assistant-facing notification events."""

    @staticmethod
    def motionDetected(location: str = "hallway", priority: str = "normal"):
        return {
            "category": "assistant.notification",
            "data": {
                "event": "motionDetected",
                "location": location,
                "priority": priority,
            },
        }

    @staticmethod
    def streamAvailable(streamId: str = "camera-bedroom-01", endpoint: str = "rtsp://localhost/stream"):
        return {
            "category": "assistant.stream.available",
            "data": {
                "streamId": streamId,
                "streamType": "rtsp",
                "endpoint": endpoint,
            },
        }

    @staticmethod
    def deviceOffline(deviceId: str = "bedroomlight1"):
        return {
            "category": "assistant.notification",
            "data": {
                "event": "deviceOffline",
                "deviceId": deviceId,
                "priority": "high",
            },
        }

    @staticmethod
    def automationCompleted(name: str = "lights.off"):
        return {
            "category": "assistant.notification",
            "data": {
                "event": "automationCompleted",
                "name": name,
                "priority": "normal",
            },
        }

    @staticmethod
    def assistantResponse(requestId: str = "abc123", success: bool = True, response: str = "Command executed successfully"):
        return {
            "category": "assistant.response",
            "data": {
                "requestId": requestId,
                "success": success,
                "response": response,
            },
        }

    @staticmethod
    def assistantError(code: str = "INVALID_INTENT", message: str = "Invalid intent"):
        return {
            "category": "assistant.error",
            "data": {
                "code": code,
                "message": message,
            },
        }

    @staticmethod
    def assistantContext(sessionId: str = "session001", interface: str = "desktop", **context):
        payload = {
            "category": "assistant.context",
            "context": {
                "sessionId": sessionId,
                "interface": interface,
            },
            "data": {
                "sessionId": sessionId,
                "interface": interface,
                "connected": True,
            },
        }
        payload["data"].update(context)
        return payload
