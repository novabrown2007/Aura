"""Home automation module facade for Aura."""

from __future__ import annotations

from core.tools.tool import Tool
from modules.base import AuraModule, ModuleMetadata
from modules.home_automation.bridgeConnection import BridgeConnection
from modules.home_automation.config import HomeAutomationConfig, buildHomeAutomationConfig
from modules.home_automation.models import (
    BridgeState,
    CameraDevice,
    Device,
    HomeAutomationNotification,
    LightDevice,
)
from modules.home_automation.serviceControl import ServiceControlConnection


class HomeAutomation(AuraModule):
    """Coordinates home automation bridge state and device actions."""

    metadata = ModuleMetadata(
        name="homeAutomation",
        version="1.0.0",
        description="Home automation bridge, service control, and device state.",
        permissions=("network:http", "process:service-control"),
        capabilities=("home-automation", "device-control"),
    )

    def __init__(self, context=None, config: HomeAutomationConfig | None = None):
        """Initialize home automation state when a context is supplied."""

        super().__init__()
        self.config = config
        self.logger = None
        self.bridge = None
        self.serviceControl = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context=None) -> BridgeState | None:
        """Initialize the module or, with no context, connect to the bridge."""

        if context is None:
            return self.bridge.connect()

        super().initialize(context)
        self.context = context
        self.config = self.config or buildHomeAutomationConfig(context)
        self.logger = context.logger.getChild("HomeAutomation") if context.logger else None
        self.bridge = BridgeConnection(self.config.bridge)
        self.serviceControl = ServiceControlConnection(self.config.control)
        return None

    def shutdown(self):
        """Shutdown home automation resources."""

    def getIntents(self):
        """Return intents handled by home automation."""

        return []

    def getTools(self):
        """Return deterministic home automation tools exposed to Aura."""

        return [
            Tool(
                name="homeAutomation.toggleLight",
                description="Turn a light on or off.",
                parameters={
                    "device_id": {"type": "string"},
                    "is_on": {"type": "boolean"},
                    "brightness": {"type": "integer"},
                },
                requiredParameters=("device_id", "is_on"),
                module="homeAutomation",
                method="toggleLight",
                safe=True,
            ),
            Tool(
                name="homeAutomation.setLightBrightness",
                description="Set light brightness.",
                parameters={"device_id": {"type": "string"}, "brightness": {"type": "integer"}},
                requiredParameters=("device_id", "brightness"),
                module="homeAutomation",
                method="setLightBrightness",
                safe=True,
            ),
            Tool(
                name="lights.setBrightness",
                description="Set a light brightness by room or light name.",
                parameters={"room": {"type": "string"}, "brightness": {"type": "integer"}},
                requiredParameters=("room", "brightness"),
                module="homeAutomation",
                method="setLightBrightnessByRoom",
                safe=True,
            ),
            Tool(
                name="lights.turnOn",
                description="Turn on a light by room or light name.",
                parameters={"room": {"type": "string"}, "brightness": {"type": "integer"}},
                requiredParameters=("room",),
                module="homeAutomation",
                method="turnLightOnByRoom",
                safe=True,
            ),
            Tool(
                name="lights.turnOff",
                description="Turn off a light by room or light name.",
                parameters={"room": {"type": "string"}},
                requiredParameters=("room",),
                module="homeAutomation",
                method="turnLightOffByRoom",
                safe=True,
            ),
            Tool(
                name="homeAutomation.setLightColor",
                description="Set light color.",
                parameters={"device_id": {"type": "string"}, "color": {"type": "string"}},
                requiredParameters=("device_id", "color"),
                module="homeAutomation",
                method="setLightColor",
                safe=True,
            ),
            Tool(
                name="homeAutomation.startCameraStream",
                description="Start a camera stream.",
                parameters={"device_id": {"type": "string"}},
                requiredParameters=("device_id",),
                module="homeAutomation",
                method="startCameraStream",
                safe=True,
            ),
            Tool(
                name="homeAutomation.stopCameraStream",
                description="Stop a camera stream.",
                parameters={"device_id": {"type": "string"}},
                requiredParameters=("device_id",),
                module="homeAutomation",
                method="stopCameraStream",
                safe=True,
            ),
            Tool(
                name="homeAutomation.takeCameraSnapshot",
                description="Take a camera snapshot.",
                parameters={"device_id": {"type": "string"}},
                requiredParameters=("device_id",),
                module="homeAutomation",
                method="takeCameraSnapshot",
                safe=True,
            ),
        ]

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

    def setLightBrightnessByRoom(self, room: str, brightness: int) -> LightDevice:
        """Set brightness for a light resolved from a room or light name."""

        return self.setLightBrightness(self._resolveLightId(room), brightness)

    def turnLightOnByRoom(self, room: str, brightness: int | None = None) -> LightDevice:
        """Turn on a light resolved from a room or light name."""

        return self.toggleLight(self._resolveLightId(room), True, brightness)

    def turnLightOffByRoom(self, room: str) -> LightDevice:
        """Turn off a light resolved from a room or light name."""

        return self.toggleLight(self._resolveLightId(room), False)

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

    def _resolveLightId(self, room: str) -> str:
        """Resolve a user-facing room/name string to a bridge light device id."""

        normalized = str(room).strip().lower()
        for light in self.getLights():
            names = {
                str(light.device_id).lower(),
                str(light.name).lower(),
                str(light.metadata.get("room", "")).lower(),
            }
            if normalized in names:
                return light.device_id
        return str(room)
