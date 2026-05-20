"""Bridge connection skeleton for Aura home automation."""

from __future__ import annotations

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

        raise NotImplementedError("Home automation bridge connection is not implemented yet.")

    def refreshDevices(self) -> BridgeState:
        """Refresh and return bridge device state."""

        return self.connect()

    def setLightState(self, device_id: str, is_on: bool, brightness: int | None = None) -> LightDevice:
        """Turn a light on or off, optionally applying brightness."""

        raise NotImplementedError("Light control is not implemented yet.")

    def setLightBrightness(self, device_id: str, brightness: int) -> LightDevice:
        """Set light brightness."""

        raise NotImplementedError("Light brightness control is not implemented yet.")

    def setLightTemperature(self, device_id: str, kelvin: int) -> LightDevice:
        """Set light color temperature."""

        raise NotImplementedError("Light temperature control is not implemented yet.")

    def setLightColor(self, device_id: str, color: str) -> LightDevice:
        """Set light color."""

        raise NotImplementedError("Light color control is not implemented yet.")

    def startCameraStream(self, device_id: str) -> CameraDevice:
        """Start a camera stream."""

        raise NotImplementedError("Camera streaming is not implemented yet.")

    def stopCameraStream(self, device_id: str) -> CameraDevice:
        """Stop a camera stream."""

        raise NotImplementedError("Camera streaming is not implemented yet.")

    def takeCameraSnapshot(self, device_id: str) -> CameraDevice:
        """Take a camera snapshot."""

        raise NotImplementedError("Camera snapshots are not implemented yet.")

    def listNotifications(self) -> list[HomeAutomationNotification]:
        """Return bridge notifications."""

        raise NotImplementedError("Bridge notifications are not implemented yet.")

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

        raise NotImplementedError("Bridge notifications are not implemented yet.")

    def getDevices(self) -> list[Device]:
        """Return all devices from the last known state."""

        return list(self._state.devices)
