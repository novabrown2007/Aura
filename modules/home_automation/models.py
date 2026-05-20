"""Data models for Aura home automation state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Device:
    """Base home automation device."""

    device_id: str
    name: str
    category: str
    online: bool = True
    last_command: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LightDevice(Device):
    """Light device state."""

    is_on: bool = False
    brightness: int = 0
    light_type: str = ""
    max_brightness: int = 100
    color_temperature_kelvin: int = 2700
    color: str = "white"


@dataclass(slots=True)
class CameraDevice(Device):
    """Camera device state."""

    status: str = "Idle"
    stream_url: str = ""
    snapshot_url: str = ""
    resolution: str = ""
    is_streaming: bool = False
    snapshot_count: int = 0


@dataclass(slots=True)
class HomeAutomationNotification:
    """Notification record returned by the automation bridge."""

    notification_id: str
    source: str
    severity: str
    category: str
    title: str
    message: str
    device_id: str = ""
    created_at: str = ""


@dataclass(slots=True)
class BridgeState:
    """Current automation bridge state."""

    connected: bool
    bridge_name: str
    lights: list[LightDevice] = field(default_factory=list)
    cameras: list[CameraDevice] = field(default_factory=list)
    devices: list[Device] = field(default_factory=list)
    last_error: str = ""

    @property
    def online_devices(self) -> int:
        """Return the number of online devices."""

        return sum(1 for device in self.devices if device.online)
