"""Environmental sensor model for Aura weather integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EnvironmentalSensor:
    """Represent one connected environmental sensor."""

    sensorId: str = ""
    name: str = ""
    sensorType: str = ""
    value: float | None = None
    unit: str = ""
    location: str = ""
    online: bool = True
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "sensorId": self.sensorId,
            "name": self.name,
            "sensorType": self.sensorType,
            "value": self.value,
            "unit": self.unit,
            "location": self.location,
            "online": bool(self.online),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        values = dict(values or {})
        return cls(
            sensorId=str(values.get("sensorId") or values.get("sensor_id") or values.get("device_id") or ""),
            name=str(values.get("name") or values.get("label") or ""),
            sensorType=str(values.get("sensorType") or values.get("sensor_type") or values.get("category") or ""),
            value=values.get("value"),
            unit=str(values.get("unit") or ""),
            location=str(values.get("location") or values.get("room") or ""),
            online=bool(values.get("online", True)),
            timestamp=str(values.get("timestamp") or values.get("updatedAt") or values.get("updated_at") or ""),
            metadata=dict(values.get("metadata") or {}),
        )
