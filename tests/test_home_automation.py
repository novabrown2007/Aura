"""Tests for the home automation module skeleton."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modules.home_automation import HomeAutomation
from modules.home_automation.config import BridgeConfig, HomeAutomationConfig, ServiceControlConfig
from modules.home_automation.models import BridgeState, CameraDevice, Device, LightDevice


class HomeAutomationSkeletonTests(unittest.TestCase):
    """Regression coverage for the initial home automation module shape."""

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

    def test_facade_accessors_return_bridge_state_views(self):
        module = HomeAutomation(SimpleNamespace(logger=None))
        light = LightDevice("light1", "Light", "light")
        camera = CameraDevice("camera1", "Camera", "camera")
        module.bridge._state = BridgeState(
            connected=True,
            bridge_name="Home",
            devices=[light, camera],
            lights=[light],
            cameras=[camera],
        )

        self.assertEqual(module.getDevices(), [light, camera])
        self.assertEqual(module.getLights(), [light])
        self.assertEqual(module.getCameras(), [camera])

    def test_facade_delegates_device_and_service_methods(self):
        module = HomeAutomation(SimpleNamespace(logger=None))

        with patch.object(module.bridge, "setLightState", return_value="light") as light_mock:
            self.assertEqual(module.toggleLight("light1", True, 50), "light")
            light_mock.assert_called_once_with("light1", True, 50)

        with patch.object(module.bridge, "startCameraStream", return_value="camera") as camera_mock:
            self.assertEqual(module.startCameraStream("camera1"), "camera")
            camera_mock.assert_called_once_with("camera1")

        with patch.object(module.serviceControl, "startBridge", return_value={"status": "ok"}) as service_mock:
            self.assertEqual(module.startBridge(), {"status": "ok"})
            service_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
