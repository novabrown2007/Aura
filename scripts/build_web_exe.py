"""Build the Aura web interface executable."""

from __future__ import annotations

import os
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
    """Build the web source bundle and package it with PyInstaller."""

    plan = buildInterfaceBundle("web")
    static_source = plan.output_dir / "interface" / "web" / "static"
    static_target = "interface/web/static"

    run([sys.executable, "-m", "pip", "install", "-r", str(plan.output_dir / "requirements.txt")])
    run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--name",
            "AuraWeb",
            "--paths",
            str(plan.output_dir),
            "--add-data",
            f"{static_source}{os.pathsep}{static_target}",
            str(plan.output_dir / plan.launcher_name),
        ]
    )
    print(f"Web executable: {ROOT / 'dist' / 'AuraWeb.exe'}")


if __name__ == "__main__":
    main()
