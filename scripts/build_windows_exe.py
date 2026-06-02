"""Build a versioned onefile Windows executable for Aura."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
ENTRY_SCRIPT = ROOT / "scripts" / "run_blank_window.py"
ICON_FILE = ROOT / "assets" / "icons" / "aura.ico"
DIST_DIR = ROOT / "dist" / "windows"
WORK_DIR = ROOT / "build" / "windows"
SPEC_DIR = ROOT / "build" / "windows"


def read_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not version:
        raise RuntimeError(f"VERSION file is empty: {VERSION_FILE}")
    return version


def main() -> None:
    version = read_version()
    exe_name = f"Aura_{version}"
    pyinstaller = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        exe_name,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--icon",
        str(ICON_FILE),
        "--add-data",
        os.pathsep.join((str(ROOT / "assets"), "assets")),
        str(ENTRY_SCRIPT),
    ]
    subprocess.run(pyinstaller, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
