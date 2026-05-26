"""Android interface testing.tests."""

from pathlib import Path
from types import SimpleNamespace
import unittest

from interface.model_status import format_current_model_label
from interface.android import AuraAndroidApp
from interface.android import aura_android_app as android_module
from modules.home_automation.models import BridgeState, LightDevice
from scripts.interface_build import createBundlePlan
from testing.tests.interfaceTests.helpers import makeInterfaceContext


class AndroidInterfaceTests(unittest.TestCase):
    """Tests that cover only the Android interface package."""

    def test_android_package_exports_app(self):
        self.assertEqual(AuraAndroidApp.__name__, "AuraAndroidApp")

    def test_android_run_requires_kivy_when_dependency_is_missing(self):
        app = AuraAndroidApp(makeInterfaceContext())
        if android_module.App is not None:
            self.skipTest("Kivy is installed in this environment.")
        with self.assertRaisesRegex(RuntimeError, "Kivy is required"):
            app.run()

    def test_android_build_plan_includes_only_android_interface(self):
        plan = createBundlePlan("android")
        self.assertIn("modules", plan.included_paths)
        self.assertIn("interface/android", plan.included_paths)
        self.assertNotIn("interface/windows", plan.included_paths)
        self.assertNotIn("interface/web", plan.included_paths)

    def test_android_build_files_exist(self):
        root = Path(__file__).resolve().parents[3]
        self.assertTrue((root / "interface" / "android" / "requirements.txt").is_file())
        self.assertTrue((root / "interface" / "android" / "build.py").is_file())

    def test_android_formats_home_automation_state(self):
        light = LightDevice("light1", "Kitchen Light", "light", is_on=True, brightness=80, color="blue")
        state = BridgeState(True, "Home", lights=[light], devices=[light])

        text = AuraAndroidApp._formatHomeAutomationState(state)

        self.assertIn("Bridge: Home", text)
        self.assertIn("Kitchen Light", text)
        self.assertIn("On 80% color=blue", text)

    def test_android_model_label_helper_uses_active_provider_model(self):
        context = SimpleNamespace(
            llmManager=SimpleNamespace(
                activeProviderName="ollama",
                providers={"ollama": SimpleNamespace(model="deepseek-r1:8b")},
            )
        )

        self.assertEqual(format_current_model_label(context), "Currently Running: deepseek-r1:8b")


if __name__ == "__main__":
    unittest.main()
