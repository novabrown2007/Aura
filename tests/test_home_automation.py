"""Tests for the home automation module."""

from __future__ import annotations

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib import error

from core.threading.events.eventManager import EventManager
from core.runtime.moduleLoader import ModuleLoader
from modules.home_automation import HomeAutomation
from modules.home_automation.bridgeConnection import BridgeConnectionError
from modules.home_automation.config import BridgeConfig, HomeAutomationConfig, ServiceControlConfig, buildHomeAutomationConfig
from modules.home_automation.models import BridgeState, CameraDevice, Device, LightDevice
from modules.home_automation.serviceControl import ServiceControlConnection, ServiceControlError
from tests.support.fakes import make_context


class FakeHttpResponse:
    """Context-manager friendly HTTP response stub."""

    def __init__(self, payload):
        if isinstance(payload, str):
            self._body = payload.encode("utf-8")
        else:
            self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None


def lightPayload(device_id="bedroomlight1", name="Bedroom Light 1", **overrides):
    payload = {
        "id": device_id,
        "name": name,
        "category": "light",
        "online": True,
        "last_command": "",
        "is_on": False,
        "brightness": 0,
        "type": "rgb",
        "max_brightness": 100,
        "color_temperature_kelvin": 2700,
        "color": "warm_white",
    }
    payload.update(overrides)
    return payload


def cameraPayload(device_id="bedroomcamera", name="Bedroom Camera", **overrides):
    payload = {
        "id": device_id,
        "name": name,
        "category": "camera",
        "online": True,
        "last_command": "",
        "status": "Idle",
        "resolution": "1080p",
        "is_streaming": False,
        "snapshot_count": 0,
    }
    payload.update(overrides)
    return payload


def devicesPayload(*devices):
    return {"devices": list(devices)}


def notificationPayload(**overrides):
    payload = {
        "id": "notification-1",
        "source": "hub",
        "severity": "warning",
        "category": "camera",
        "title": "Motion detected",
        "message": "Motion detected for bedroomcamera.",
        "device_id": "bedroomcamera",
        "created_at": "2026-05-07 12:00:00",
    }
    payload.update(overrides)
    return payload


def makeModule():
    config = HomeAutomationConfig(
        bridge=BridgeConfig(),
        control=ServiceControlConfig(),
    )
    return HomeAutomation(SimpleNamespace(logger=None, config=None), config=config)


class HomeAutomationConfigTests(unittest.TestCase):
    """Configuration and model tests."""

    def test_config_builds_bridge_and_control_base_urls(self):
        config = HomeAutomationConfig(
            bridge=BridgeConfig(host="bridge.local", port=8443, use_ssl=True),
            control=ServiceControlConfig(host="control.local", port=8091),
        )

        self.assertEqual(config.bridge.base_url, "https://bridge.local:8443")
        self.assertEqual(config.control.base_url, "http://control.local:8091")

    def test_bridge_state_counts_online_devices(self):
        state = BridgeState(
            connected=True,
            bridge_name="Home",
            devices=[
                Device("sensor1", "Sensor", "sensor", online=True),
                Device("camera1", "Camera", "camera", online=False),
            ],
        )

        self.assertEqual(state.online_devices, 1)

    def test_build_config_reads_aura_config_values(self):
        aura_config = SimpleNamespace(
            get=lambda key, default=None: {
                "home_automation.bridge.host": "bridge.local",
                "home_automation.bridge.use_ssl": "true",
                "home_automation.control.use_ssl": "false",
            }.get(key, default)
        )

        config = buildHomeAutomationConfig(SimpleNamespace(config=aura_config))

        self.assertEqual(config.bridge.host, "bridge.local")
        self.assertTrue(config.bridge.use_ssl)
        self.assertFalse(config.control.use_ssl)


class BridgeConnectionTests(unittest.TestCase):
    """Bridge connectivity and payload parsing tests."""

    def test_connect_builds_live_state_from_devices_payload(self):
        module = makeModule()
        payload = devicesPayload(
            lightPayload(last_command="light_on", is_on=True, brightness=80),
            cameraPayload(last_command="start_stream", status="Streaming", is_streaming=True),
        )

        with patch.object(module.bridge, "_requestJson", return_value=payload):
            state = module.initialize()

        self.assertTrue(state.connected)
        self.assertEqual(state.bridge_name, "Home Automation Bridge")
        self.assertEqual(state.online_devices, 2)
        self.assertEqual(state.lights[0].last_command, "light_on")
        self.assertTrue(state.cameras[0].is_streaming)

    def test_refresh_devices_reloads_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(lightPayload(brightness=0)),
                devicesPayload(lightPayload(brightness=55)),
            ],
        ):
            module.initialize()
            refreshed = module.refresh()

        self.assertEqual(refreshed.lights[0].brightness, 55)

    def test_connect_returns_unavailable_state_on_failure(self):
        module = makeModule()

        with patch.object(module.bridge, "_requestJson", side_effect=BridgeConnectionError("connection refused")):
            state = module.initialize()

        self.assertFalse(state.connected)
        self.assertEqual(state.bridge_name, "Unavailable")
        self.assertIn("connection refused", state.last_error)

    def test_request_json_parses_http_response_body(self):
        module = makeModule()

        with patch("modules.home_automation.bridgeConnection.request.urlopen", return_value=FakeHttpResponse({"status": "ok"})):
            payload = module.bridge._requestJson("GET", "/devices")

        self.assertEqual(payload, {"status": "ok"})

    def test_request_json_raises_for_invalid_json(self):
        module = makeModule()

        with patch("modules.home_automation.bridgeConnection.request.urlopen", return_value=FakeHttpResponse("not-json")):
            with self.assertRaises(BridgeConnectionError):
                module.bridge._requestJson("GET", "/devices")

    def test_request_json_raises_for_url_error(self):
        module = makeModule()

        with patch("modules.home_automation.bridgeConnection.request.urlopen", side_effect=error.URLError("boom")):
            with self.assertRaises(BridgeConnectionError):
                module.bridge._requestJson("GET", "/devices")

    def test_list_notifications_parses_notification_payload(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            return_value={"notifications": [notificationPayload(title="Bridge alert")]},
        ):
            notifications = module.getNotifications()

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].title, "Bridge alert")
        self.assertEqual(notifications[0].device_id, "bedroomcamera")

    def test_queue_notification_posts_to_bridge(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            return_value={"status": "ok", "notification_id": "notification-9"},
        ) as request_mock:
            response = module.queueNotification("ui", "info", "system", "Startup", "UI started.")

        self.assertEqual(response["notification_id"], "notification-9")
        request_mock.assert_called_once()
        self.assertEqual(request_mock.call_args.args[0], "POST")
        self.assertEqual(request_mock.call_args.args[1], "/notifications")


class LightControlTests(unittest.TestCase):
    """Light control tests."""

    def test_toggle_light_updates_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(lightPayload(device_id="bedroomlight2")),
                {"status": "ok"},
                devicesPayload(lightPayload(device_id="bedroomlight2", is_on=True, brightness=90, last_command="light_on")),
                {"status": "ok"},
                devicesPayload(lightPayload(device_id="bedroomlight2", is_on=True, brightness=55, last_command="set_brightness")),
            ],
        ):
            module.initialize()
            updated = module.toggleLight("bedroomlight2", True, 55)

        self.assertIsInstance(updated, LightDevice)
        self.assertTrue(updated.is_on)
        self.assertEqual(updated.brightness, 55)
        self.assertEqual(updated.last_command, "set_brightness")

    def test_set_light_brightness_updates_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(lightPayload()),
                {"status": "ok"},
                devicesPayload(lightPayload(brightness=42, is_on=True, last_command="set_brightness")),
            ],
        ):
            module.initialize()
            updated = module.setLightBrightness("bedroomlight1", 42)

        self.assertEqual(updated.brightness, 42)
        self.assertTrue(updated.is_on)
        self.assertEqual(updated.last_command, "set_brightness")

    def test_set_light_temperature_updates_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(lightPayload()),
                {"status": "ok"},
                devicesPayload(lightPayload(color_temperature_kelvin=4100, last_command="set_temperature")),
            ],
        ):
            module.initialize()
            updated = module.setLightTemperature("bedroomlight1", 4100)

        self.assertEqual(updated.color_temperature_kelvin, 4100)
        self.assertEqual(updated.last_command, "set_temperature")

    def test_set_light_color_updates_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(lightPayload()),
                {"status": "ok"},
                devicesPayload(lightPayload(color="blue", last_command="set_color")),
            ],
        ):
            module.initialize()
            updated = module.setLightColor("bedroomlight1", "blue")

        self.assertEqual(updated.color, "blue")
        self.assertEqual(updated.last_command, "set_color")

    def test_light_changes_emit_event(self):
        context = make_context()
        context.eventManager = EventManager(context)
        received = []
        context.eventManager.subscribe("lights.changed", received.append)
        config = HomeAutomationConfig(
            bridge=BridgeConfig(),
            control=ServiceControlConfig(),
        )
        module = HomeAutomation(context, config=config)

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(lightPayload()),
                {"status": "ok"},
                devicesPayload(lightPayload(brightness=42, is_on=True, last_command="set_brightness")),
            ],
        ):
            module.initialize()
            module.setLightBrightness("bedroomlight1", 42)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].name, "lights.changed")
        self.assertEqual(received[0].data["device_id"], "bedroomlight1")
        self.assertEqual(received[0].data["light"]["brightness"], 42)


class CameraControlTests(unittest.TestCase):
    """Camera control tests."""

    def test_start_camera_stream_updates_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(cameraPayload()),
                {"status": "ok"},
                devicesPayload(cameraPayload(is_streaming=True, status="Streaming", last_command="start_stream")),
            ],
        ):
            module.initialize()
            updated = module.startCameraStream("bedroomcamera")

        self.assertIsInstance(updated, CameraDevice)
        self.assertTrue(updated.is_streaming)
        self.assertEqual(updated.status, "Streaming")
        self.assertEqual(updated.last_command, "start_stream")

    def test_stop_camera_stream_updates_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(cameraPayload(is_streaming=True, status="Streaming")),
                {"status": "ok"},
                devicesPayload(cameraPayload(is_streaming=False, status="Idle", last_command="stop_stream")),
            ],
        ):
            module.initialize()
            updated = module.stopCameraStream("bedroomcamera")

        self.assertFalse(updated.is_streaming)
        self.assertEqual(updated.status, "Idle")
        self.assertEqual(updated.last_command, "stop_stream")

    def test_take_camera_snapshot_updates_state(self):
        module = makeModule()

        with patch.object(
            module.bridge,
            "_requestJson",
            side_effect=[
                devicesPayload(cameraPayload(snapshot_count=0)),
                {"status": "ok"},
                devicesPayload(cameraPayload(snapshot_count=1, last_command="take_snapshot")),
            ],
        ):
            module.initialize()
            updated = module.takeCameraSnapshot("bedroomcamera")

        self.assertEqual(updated.snapshot_count, 1)
        self.assertEqual(updated.last_command, "take_snapshot")


class ServiceControlTests(unittest.TestCase):
    """Remote backend service startup control tests."""

    def test_start_bridge_posts_to_control_endpoint(self):
        control = ServiceControlConnection(ServiceControlConfig())

        with patch("modules.home_automation.serviceControl.request.urlopen", return_value=FakeHttpResponse({"status": "ok"})) as urlopen_mock:
            payload = control.startBridge()

        self.assertEqual(payload["status"], "ok")
        request_obj = urlopen_mock.call_args.args[0]
        self.assertEqual(request_obj.method, "POST")
        self.assertTrue(request_obj.full_url.endswith("/control/startbridge"))

    def test_start_hub_posts_to_control_endpoint(self):
        control = ServiceControlConnection(ServiceControlConfig())

        with patch("modules.home_automation.serviceControl.request.urlopen", return_value=FakeHttpResponse({"status": "ok"})) as urlopen_mock:
            payload = control.startHub()

        self.assertEqual(payload["status"], "ok")
        request_obj = urlopen_mock.call_args.args[0]
        self.assertEqual(request_obj.method, "POST")
        self.assertTrue(request_obj.full_url.endswith("/control/starthub"))

    def test_service_control_raises_for_unreachable_endpoint(self):
        control = ServiceControlConnection(ServiceControlConfig())

        with patch("modules.home_automation.serviceControl.request.urlopen", side_effect=error.URLError("boom")):
            with self.assertRaises(ServiceControlError):
                control.startBridge()


class HomeAutomationRegistrationTests(unittest.TestCase):
    """Runtime integration tests for module registration."""

    def test_module_loader_registers_home_automation(self):
        context = SimpleNamespace(logger=None, config=None)

        ModuleLoader(context).loadModules()

        self.assertIsInstance(context.homeAutomation, HomeAutomation)


if __name__ == "__main__":
    unittest.main()
