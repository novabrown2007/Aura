"""Prepare and build the Aura Android APK with Buildozer under WSL."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.interface_build import buildInterfaceBundle  # noqa: E402


def wsl_path(path: Path) -> str:
    """Convert a Windows path under a drive root to a WSL mount path."""

    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    parts = [part for part in resolved.parts[1:]]
    return f"/mnt/{drive}/" + "/".join(parts)


def run(command: list[str]):
    """Run one build command from the project root."""

    print("+ " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def configure_buildozer_spec(spec_path: Path):
    """Apply Aura defaults to a generated Buildozer spec file."""

    replacements = {
        "title": "Aura",
        "package.name": "aura",
        "package.domain": "org.novabrown",
        "source.include_exts": "py,png,jpg,kv,json,yml,txt",
        "requirements": "python3,kivy,requests,PyYAML,mysql-connector-python,tzdata,google-genai",
        "orientation": "portrait",
    }

    lines = spec_path.read_text(encoding="utf-8").splitlines()
    seen = set()
    updated = []
    for line in lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if key in replacements:
            updated.append(f"{key} = {replacements[key]}")
            seen.add(key)
            continue
        updated.append(line)

    for key, value in replacements.items():
        if key not in seen:
            updated.append(f"{key} = {value}")

    spec_path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def main():
    """Build the Android bundle, create main.py, and run Buildozer debug build."""

    plan = buildInterfaceBundle("android")
    launcher = plan.output_dir / plan.launcher_name
    main_py = plan.output_dir / "main.py"
    shutil.copy2(launcher, main_py)
    print(f"Android Buildozer entrypoint: {main_py}")

    build_dir = wsl_path(plan.output_dir)
    run(
        [
            "wsl.exe",
            "bash",
            "-lc",
            f"cd '{build_dir}' && python3 -m pip install --user buildozer cython && "
            "test -f buildozer.spec || buildozer init",
        ]
    )
    configure_buildozer_spec(plan.output_dir / "buildozer.spec")
    run(["wsl.exe", "bash", "-lc", f"cd '{build_dir}' && buildozer android debug"])
    print(f"Android APK directory: {plan.output_dir / 'bin'}")


if __name__ == "__main__":
    main()
