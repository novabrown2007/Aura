"""Build the Windows Aura interface executable."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.interface_build import buildInterfaceBundle  # noqa: E402


def run(command: list[str]):
    """Run one build command from the project root."""

    print("+ " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    """Build the Windows source bundle and package it with PyInstaller."""

    plan = buildInterfaceBundle("windows")
    run([sys.executable, "-m", "pip", "install", "-r", str(plan.output_dir / "requirements.txt")])
    run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--name",
            "AuraWindows",
            "--paths",
            str(plan.output_dir),
            "--icon",
            str(ROOT / "assets" / "icons" / "aura.ico"),
            str(plan.output_dir / plan.launcher_name),
        ]
    )
    print(f"Windows executable: {ROOT / 'dist' / 'AuraWindows.exe'}")


if __name__ == "__main__":
    main()
