"""Build helper for generating `Aura.exe` on Windows."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def build():
    """
    Build the Aura Windows executable using PyInstaller.
    """

    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        venv_pyinstaller = Path(sys.executable).resolve().parent / "pyinstaller.exe"
        if venv_pyinstaller.exists():
            pyinstaller = str(venv_pyinstaller)

    if not pyinstaller:
        raise RuntimeError("PyInstaller is not installed. Install it with: pip install pyinstaller")

    project_root = Path(__file__).resolve().parents[4]
    entrypoint = (
        project_root
        / "core"
        / "interface"
        / "desktopInterface"
        / "windows"
        / "runAuraWindows.py"
    )

    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--name",
        "Aura",
        "--windowed",
        "--onefile",
        str(entrypoint),
    ]

    result = subprocess.run(command, cwd=project_root, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with exit code {result.returncode}.")


if __name__ == "__main__":
    try:
        build()
        print("Build complete. Executable is in dist/Aura.exe")
    except Exception as error:
        print(f"Build failed: {error}")
        sys.exit(1)
