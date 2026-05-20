"""Windows interface tests."""

from pathlib import Path
import unittest

from interface.windows import AuraWindowsApp
from modules.home_automation.models import BridgeState, LightDevice
from scripts.interface_build import createBundlePlan


class WindowsInterfaceTests(unittest.TestCase):
    """Tests that cover only the Windows interface package."""

    def test_windows_package_exports_app(self):
        self.assertEqual(AuraWindowsApp.__name__, "AuraWindowsApp")

    def test_windows_build_plan_includes_only_windows_interface(self):
        plan = createBundlePlan("windows")
        self.assertIn("modules", plan.included_paths)
        self.assertIn("interface/windows", plan.included_paths)
        self.assertNotIn("interface/android", plan.included_paths)
        self.assertNotIn("interface/web", plan.included_paths)

    def test_windows_build_files_exist(self):
        root = Path(__file__).resolve().parents[2]
        self.assertTrue((root / "interface" / "windows" / "requirements.txt").is_file())
        self.assertTrue((root / "interface" / "windows" / "build.py").is_file())

    def test_windows_formats_home_automation_state(self):
        light = LightDevice("light1", "Kitchen Light", "light", is_on=True, brightness=80)
        state = BridgeState(True, "Home", lights=[light], devices=[light])

        text = AuraWindowsApp._formatHomeAutomationState(None, state)

        self.assertIn("Bridge: Home", text)
        self.assertIn("Kitchen Light", text)
        self.assertIn("on 80%", text)


if __name__ == "__main__":
    unittest.main()
