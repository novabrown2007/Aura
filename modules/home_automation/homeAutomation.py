"""Home automation module facade for Aura."""

from __future__ import annotations

from modules.home_automation.bridgeConnection import BridgeConnection
from modules.home_automation.config import HomeAutomationConfig
from modules.home_automation.models import (
    BridgeState,
    CameraDevice,
    Device,
    HomeAutomationNotification,
    LightDevice,
)
from modules.home_automation.serviceControl import ServiceControlConnection


class HomeAutomation:
    """Coordinates home automation bridge state and device actions."""

    def __init__(self, context, config: HomeAutomationConfig | None = None):
        self.context = context
        self.config = config or HomeAutomationConfig()
        self.logger = context.logger.getChild("HomeAutomation") if context.logger else None
        self.bridge = BridgeConnection(self.config.bridge)
        self.serviceControl = ServiceControlConnection(self.config.control)

    def initialize(self) -> BridgeState:
        """Initialize the bridge state."""

        return self.bridge.connect()

    def refresh(self) -> BridgeState:
        """Refresh bridge state."""

        return self.bridge.refreshDevices()

    def getBridgeState(self) -> BridgeState:
        """Return the last known bridge state."""

        return self.bridge.state

    def getDevices(self) -> list[Device]:
        """Return all known devices."""

        return list(self.bridge.state.devices)

    def getLights(self) -> list[LightDevice]:
        """Return known lights."""

        return list(self.bridge.state.lights)

    def getCameras(self) -> list[CameraDevice]:
        """Return known cameras."""

        return list(self.bridge.state.cameras)

    def toggleLight(self, device_id: str, is_on: bool, brightness: int | None = None) -> LightDevice:
        """Turn a light on or off."""

        return self.bridge.setLightState(device_id, is_on, brightness)

    def setLightBrightness(self, device_id: str, brightness: int) -> LightDevice:
        """Set light brightness."""

        return self.bridge.setLightBrightness(device_id, brightness)

    def setLightTemperature(self, device_id: str, kelvin: int) -> LightDevice:
        """Set light color temperature."""

        return self.bridge.setLightTemperature(device_id, kelvin)

    def setLightColor(self, device_id: str, color: str) -> LightDevice:
        """Set light color."""

        return self.bridge.setLightColor(device_id, color)

    def startCameraStream(self, device_id: str) -> CameraDevice:
        """Start a camera stream."""

        return self.bridge.startCameraStream(device_id)

    def stopCameraStream(self, device_id: str) -> CameraDevice:
        """Stop a camera stream."""

        return self.bridge.stopCameraStream(device_id)

    def takeCameraSnapshot(self, device_id: str) -> CameraDevice:
        """Take a camera snapshot."""

        return self.bridge.takeCameraSnapshot(device_id)

    def getNotifications(self) -> list[HomeAutomationNotification]:
        """Return bridge notifications."""

        return self.bridge.listNotifications()

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

        return self.bridge.queueNotification(source, severity, category, title, message, device_id)

    def startBridge(self) -> dict[str, object]:
        """Start the bridge service through service control."""

        return self.serviceControl.startBridge()

    def startHub(self) -> dict[str, object]:
        """Start the hub service through service control."""

        return self.serviceControl.startHub()
