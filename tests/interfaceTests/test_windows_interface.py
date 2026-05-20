"""Windows interface tests."""

from pathlib import Path
import unittest

from interface.windows import AuraWindowsApp
from scripts.interface_build import createBundlePlan


class WindowsInterfaceTests(unittest.TestCase):
    """Tests that cover only the Windows interface package."""

    def test_windows_package_exports_app(self):
        self.assertEqual(AuraWindowsApp.__name__, "AuraWindowsApp")

    def test_windows_build_plan_includes_only_windows_interface(self):
        plan = createBundlePlan("windows")
        self.assertIn("interface/windows", plan.included_paths)
        self.assertNotIn("interface/android", plan.included_paths)
        self.assertNotIn("interface/web", plan.included_paths)

    def test_windows_build_files_exist(self):
        root = Path(__file__).resolve().parents[2]
        self.assertTrue((root / "interface" / "windows" / "requirements.txt").is_file())
        self.assertTrue((root / "interface" / "windows" / "build.py").is_file())


if __name__ == "__main__":
    unittest.main()
