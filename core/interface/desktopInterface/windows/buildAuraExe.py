"""Build helper for generating `aura.exe` on Windows.

This script wraps PyInstaller with project-specific defaults so the
Windows interface can be packaged without remembering CLI flags.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def build():
    """Build the Aura Windows executable using PyInstaller.

    Raises:
        RuntimeError:
            If PyInstaller is not installed or the build fails.
    """

    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        venv_pyinstaller = Path(sys.executable).resolve().parent / "pyinstaller.exe"
        if venv_pyinstaller.exists():
            pyinstaller = str(venv_pyinstaller)

    if not pyinstaller:
        raise RuntimeError(
            "PyInstaller is not installed. Install it with: pip install pyinstaller"
        )

    project_root = Path(__file__).resolve().parents[4]
    entrypoint = project_root / "core" / "interface" / "desktopInterface" / "windows" / "runAuraWindows.py"
    icon_path = project_root / "assets" / "icons" / "aura.ico"

    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--name",
        "aura",
        "--windowed",
        "--onefile",
        "--hidden-import",
        "modules.commands",
        "--hidden-import",
        "modules.reminders",
        str(entrypoint),
    ]

    if icon_path.exists():
        command.extend(["--icon", str(icon_path)])
        command.extend(["--add-data", f"{icon_path};assets\\icons"])

    result = subprocess.run(command, cwd=project_root, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {result.returncode}.")


if __name__ == "__main__":
    try:
        build()
        print("Build complete. Executable is in dist/aura.exe")
    except Exception as error:
        print(f"Build failed: {error}")
        sys.exit(1)
