"""Android interface tests."""

from pathlib import Path
import unittest

from interface.android import AuraAndroidApp
from interface.android import aura_android_app as android_module
from scripts.interface_build import createBundlePlan
from tests.interfaceTests.helpers import makeInterfaceContext


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
        self.assertIn("interface/android", plan.included_paths)
        self.assertNotIn("interface/windows", plan.included_paths)
        self.assertNotIn("interface/web", plan.included_paths)

    def test_android_build_files_exist(self):
        root = Path(__file__).resolve().parents[2]
        self.assertTrue((root / "interface" / "android" / "requirements.txt").is_file())
        self.assertTrue((root / "interface" / "android" / "build.py").is_file())


if __name__ == "__main__":
    unittest.main()
