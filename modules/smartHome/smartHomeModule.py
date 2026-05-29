"""Mock smart home capability module for Aura."""

from __future__ import annotations

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata
from modules.smartHome.smartHomeActions import SMART_HOME_ACTIONS
from modules.smartHome.smartHomeEvents import SmartHomeEvents
from modules.smartHome.smartHomeIntents import SMART_HOME_INTENTS
from modules.smartHome.smartHomePermissions import SMART_HOME_PERMISSIONS


class SmartHomeModule(AuraModule):
    """Deterministic smart home capability placeholder."""

    metadata = ModuleMetadata(
        name="smartHome",
        version="1.0.0",
        author="Aura",
        description="Local smart home capability placeholder.",
        permissions=tuple(SMART_HOME_PERMISSIONS.asList()),
        capabilities=("smart-home.control", "smart-home.status"),
    )

    def __init__(self, context=None):
        super().__init__()
        self.lights: dict[str, dict[str, object]] = {}
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        super().initialize(context)
        if self.logger:
            self.logger.info("smartHome module started.")

    def getIntents(self):
        return list(SMART_HOME_INTENTS)

    def getActions(self):
        return list(SMART_HOME_ACTIONS)

    def getPermissions(self):
        return SMART_HOME_PERMISSIONS

    def turnLightOn(self, room: str) -> dict[str, object]:
        return self._setLightState(room, isOn=True)

    def turnLightOff(self, room: str) -> dict[str, object]:
        return self._setLightState(room, isOn=False)

    def setLightColor(self, room: str, color: str) -> dict[str, object]:
        state = self._setLightState(room)
        state["color"] = str(color or "")
        self.emit(SmartHomeEvents.LIGHT_CHANGED, dict(state))
        return state

    def getLightState(self, room: str) -> dict[str, object]:
        return dict(self.lights.get(self._normalizeRoom(room), {"room": str(room or ""), "isOn": False, "color": ""}))

    def _setLightState(self, room: str, isOn: bool | None = None) -> dict[str, object]:
        key = self._normalizeRoom(room)
        state = dict(self.lights.get(key, {"room": str(room or ""), "isOn": False, "color": ""}))
        if isOn is not None:
            state["isOn"] = bool(isOn)
        self.lights[key] = state
        self.emit(SmartHomeEvents.REQUESTED, dict(state))
        self.emit(SmartHomeEvents.LIGHT_CHANGED, dict(state))
        return state

    @staticmethod
    def _normalizeRoom(room: str) -> str:
        return str(room or "").strip().lower().replace(" ", "_")
