"""Bridge connection skeleton for Aura home automation."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from modules.home_automation.config import BridgeConfig
from modules.home_automation.models import (
    BridgeState,
    CameraDevice,
    Device,
    HomeAutomationNotification,
    LightDevice,
)


class BridgeConnectionError(RuntimeError):
    """Raised when the home automation bridge cannot complete a request."""


class BridgeConnection:
    """Connection boundary for home automation bridge operations."""

    def __init__(self, config: BridgeConfig):
        self.config = config
        self._state = BridgeState(connected=False, bridge_name="Unavailable")

    @property
    def state(self) -> BridgeState:
        """Return the last known bridge state."""

        return self._state

    def connect(self) -> BridgeState:
        """Connect to the bridge and return the current state."""

        try:
            devices_payload = self._requestJson("GET", "/devices")
        except BridgeConnectionError as error:
            self._state = BridgeState(
                connected=False,
                bridge_name="Unavailable",
                last_error=str(error),
            )
            return self._state

        self._state = self._buildState(devices_payload)
        return self._state

    def refreshDevices(self) -> BridgeState:
        """Refresh and return bridge device state."""

        return self.connect()

    def setLightState(self, device_id: str, is_on: bool, brightness: int | None = None) -> LightDevice:
        """Turn a light on or off, optionally applying brightness."""

        payload: dict[str, Any] = {"is_on": is_on}
        route = f"/light/on/{device_id}" if is_on else f"/light/off/{device_id}"
        self._requestJson("POST", route, payload)

        self.refreshDevices()
        light = self._findLight(device_id, f"Bridge accepted command but light '{device_id}' is missing from /devices.")

        if brightness is not None:
            light = self.setLightBrightness(device_id, brightness)

        return light

    def setLightBrightness(self, device_id: str, brightness: int) -> LightDevice:
        """Set light brightness."""

        brightness = max(0, min(100, int(brightness)))
        self._requestJson("POST", f"/light/brightness/{device_id}/{brightness}", {})
        self.refreshDevices()
        return self._findLight(device_id, f"Light '{device_id}' missing after brightness update.")

    def setLightTemperature(self, device_id: str, kelvin: int) -> LightDevice:
        """Set light color temperature."""

        self._requestJson("POST", f"/light/temp/{device_id}/{int(kelvin)}", {})
        self.refreshDevices()
        return self._findLight(device_id, f"Light '{device_id}' missing after temperature update.")

    def setLightColor(self, device_id: str, color: str) -> LightDevice:
        """Set light color."""

        encoded_color = parse.quote(str(color), safe="")
        self._requestJson("POST", f"/light/color/{device_id}/{encoded_color}", {})
        self.refreshDevices()
        return self._findLight(device_id, f"Light '{device_id}' missing after color update.")

    def startCameraStream(self, device_id: str) -> CameraDevice:
        """Start a camera stream."""

        self._requestJson("POST", f"/camera/start/{device_id}", {})
        self.refreshDevices()
        return self._findCamera(device_id, f"Camera '{device_id}' missing after start stream.")

    def stopCameraStream(self, device_id: str) -> CameraDevice:
        """Stop a camera stream."""

        self._requestJson("POST", f"/camera/stop/{device_id}", {})
        self.refreshDevices()
        return self._findCamera(device_id, f"Camera '{device_id}' missing after stop stream.")

    def takeCameraSnapshot(self, device_id: str) -> CameraDevice:
        """Take a camera snapshot."""

        self._requestJson("POST", f"/camera/snapshot/{device_id}", {})
        self.refreshDevices()
        return self._findCamera(device_id, f"Camera '{device_id}' missing after snapshot.")

    def listNotifications(self) -> list[HomeAutomationNotification]:
        """Return bridge notifications."""

        payload = self._requestJson("GET", "/notifications")
        raw_notifications = payload.get("notifications", [])
        if not isinstance(raw_notifications, list):
            raise BridgeConnectionError("Bridge /notifications response must contain a 'notifications' list.")
        return [self._parseNotification(item) for item in raw_notifications]

    def queueNotification(
        self,
        source: str,
        severity: str,
        category: str,
        title: str,
        message: str,
        device_id: str = "",
    ) -> dict[str, object]:
        """Queue a bridge notification."""

        return self._requestJson(
            "POST",
            "/notifications",
            {
                "source": source,
                "severity": severity,
                "category": category,
                "title": title,
                "message": message,
                "device_id": device_id,
            },
        )

    def getDevices(self) -> list[Device]:
        """Return all devices from the last known state."""

        return list(self._state.devices)

    def _requestJson(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one JSON request to the bridge."""

        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"

        bridge_request = request.Request(
            url=f"{self.config.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(bridge_request, timeout=self.config.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except error.URLError as exception:
            reason = getattr(exception, "reason", exception)
            raise BridgeConnectionError(f"Failed to reach bridge at {self.config.base_url}: {reason}") from exception
        except OSError as exception:
            raise BridgeConnectionError(f"Bridge request failed: {exception}") from exception

        try:
            parsed = json.loads(raw_body or "{}")
        except json.JSONDecodeError as exception:
            raise BridgeConnectionError(f"Bridge returned invalid JSON for {path}.") from exception

        if not isinstance(parsed, dict):
            raise BridgeConnectionError(f"Bridge returned an unexpected payload for {path}.")
        return parsed

    def _buildState(self, devices_payload: dict[str, Any]) -> BridgeState:
        """Build a BridgeState from a bridge /devices payload."""

        raw_devices = devices_payload.get("devices", [])
        if not isinstance(raw_devices, list):
            raise BridgeConnectionError("Bridge /devices response must contain a 'devices' list.")

        devices: list[Device] = []
        lights: list[LightDevice] = []
        cameras: list[CameraDevice] = []

        for item in raw_devices:
            if not isinstance(item, dict):
                raise BridgeConnectionError("Bridge device entries must be objects.")
            category = str(item.get("category", "")).lower() or self._inferCategory(str(item.get("device_id", item.get("id", ""))))
            if category == "light":
                light = self._parseLight(item)
                lights.append(light)
                devices.append(light)
            elif category == "camera":
                camera = self._parseCamera(item)
                cameras.append(camera)
                devices.append(camera)
            else:
                devices.append(self._parseDevice(item))

        return BridgeState(
            connected=True,
            bridge_name="Home Automation Bridge",
            lights=lights,
            cameras=cameras,
            devices=devices,
            last_error="",
        )

    @staticmethod
    def _parseDevice(item: dict[str, Any]) -> Device:
        """Parse a generic device payload."""

        category = str(item.get("category", "")).lower() or BridgeConnection._inferCategory(str(item.get("id", "")))
        return Device(
            device_id=str(item.get("device_id", item.get("id", ""))),
            name=str(item.get("name", "Unknown Device")),
            category=category or "device",
            online=bool(item.get("online", True)),
            last_command=str(item.get("last_command", "")),
            metadata=dict(item.get("metadata", {})),
        )

    @staticmethod
    def _parseLight(item: dict[str, Any]) -> LightDevice:
        """Parse a light device payload."""

        base = BridgeConnection._parseDevice(item)
        return LightDevice(
            device_id=base.device_id,
            name=base.name,
            category="light",
            online=base.online,
            last_command=base.last_command,
            metadata=base.metadata,
            is_on=bool(item.get("is_on", False)),
            brightness=int(item.get("brightness", 0)),
            light_type=str(item.get("light_type", item.get("type", ""))),
            max_brightness=int(item.get("max_brightness", item.get("maxBrightness", 100))),
            color_temperature_kelvin=int(item.get("color_temperature_kelvin", item.get("kelvin", 2700))),
            color=str(item.get("color", "white")),
        )

    @staticmethod
    def _parseCamera(item: dict[str, Any]) -> CameraDevice:
        """Parse a camera device payload."""

        base = BridgeConnection._parseDevice(item)
        return CameraDevice(
            device_id=base.device_id,
            name=base.name,
            category="camera",
            online=base.online,
            last_command=base.last_command,
            metadata=base.metadata,
            status=str(item.get("status", "Idle")),
            stream_url=str(item.get("stream_url", "")),
            snapshot_url=str(item.get("snapshot_url", "")),
            resolution=str(item.get("resolution", "")),
            is_streaming=bool(item.get("is_streaming", False)),
            snapshot_count=int(item.get("snapshot_count", 0)),
        )

    @staticmethod
    def _parseNotification(item: dict[str, Any]) -> HomeAutomationNotification:
        """Parse a bridge notification payload."""

        return HomeAutomationNotification(
            notification_id=str(item.get("notification_id", item.get("id", ""))),
            source=str(item.get("source", "")),
            severity=str(item.get("severity", "info")),
            category=str(item.get("category", "system")),
            title=str(item.get("title", "")),
            message=str(item.get("message", "")),
            device_id=str(item.get("device_id", "")),
            created_at=str(item.get("created_at", "")),
        )

    def _findLight(self, device_id: str, error_message: str) -> LightDevice:
        light = next((item for item in self._state.lights if item.device_id == device_id), None)
        if light is None:
            raise BridgeConnectionError(error_message)
        return light

    def _findCamera(self, device_id: str, error_message: str) -> CameraDevice:
        camera = next((item for item in self._state.cameras if item.device_id == device_id), None)
        if camera is None:
            raise BridgeConnectionError(error_message)
        return camera

    @staticmethod
    def _inferCategory(device_id: str) -> str:
        normalized = device_id.lower()
        if "light" in normalized:
            return "light"
        if "camera" in normalized:
            return "camera"
        return "device"
