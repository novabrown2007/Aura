"""Build source bundles for Aura interface targets."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "build" / "interfaces"
COMMON_PATHS = (
    "config",
    "core",
    "modules",
    "main.py",
)


LAUNCHERS = {
    "windows": """\
from main import buildRuntimeContext, shutdown, startup
from interface.windows import AuraWindowsApp


def main():
    context = buildRuntimeContext()
    startup(context)
    try:
        AuraWindowsApp(context).run()
    finally:
        shutdown(context)
        if context.logger:
            context.logger.close()


if __name__ == "__main__":
    main()
""",
    "android": """\
from main import buildRuntimeContext, shutdown, startup
from interface.android import AuraAndroidApp


def main():
    context = buildRuntimeContext()
    startup(context)
    try:
        AuraAndroidApp(context).run()
    finally:
        shutdown(context)
        if context.logger:
            context.logger.close()


if __name__ == "__main__":
    main()
""",
    "web": """\
from main import buildRuntimeContext, shutdown, startup
from interface.web import AuraWebApp


def main():
    context = buildRuntimeContext()
    startup(context)
    try:
        AuraWebApp(context).serve_forever()
    finally:
        shutdown(context)
        if context.logger:
            context.logger.close()


if __name__ == "__main__":
    main()
""",
}


@dataclass(frozen=True)
class BundlePlan:
    """Description of one interface bundle build."""

    platform: str
    output_dir: Path
    archive_path: Path
    included_paths: tuple[str, ...]
    launcher_name: str


def buildInterfaceBundle(platform: str, clean: bool = True, zip_bundle: bool = True) -> BundlePlan:
    """Build one interface bundle from shared backend files and one interface package."""

    plan = createBundlePlan(platform)
    if clean and plan.output_dir.exists():
        shutil.rmtree(plan.output_dir)

    plan.output_dir.mkdir(parents=True, exist_ok=True)

    for relative_path in plan.included_paths:
        _copyPath(ROOT / relative_path, plan.output_dir / relative_path)

    _writeRequirements(platform, plan.output_dir / "requirements.txt")
    _writeLauncher(platform, plan.output_dir / plan.launcher_name)
    _writeManifest(plan)

    if zip_bundle:
        _writeArchive(plan)

    return plan


def createBundlePlan(platform: str) -> BundlePlan:
    """Create a build plan for a supported interface platform."""

    normalized = str(platform).strip().lower()
    if normalized not in LAUNCHERS:
        supported = ", ".join(sorted(LAUNCHERS))
        raise ValueError(f"Unsupported interface platform '{platform}'. Use one of: {supported}.")

    included = (
        *COMMON_PATHS,
        "interface/__init__.py",
        f"interface/{normalized}",
    )
    output_dir = BUILD_ROOT / normalized
    return BundlePlan(
        platform=normalized,
        output_dir=output_dir,
        archive_path=BUILD_ROOT / f"aura_{normalized}.zip",
        included_paths=included,
        launcher_name=f"run_aura_{normalized}.py",
    )


def _copyPath(source: Path, destination: Path):
    if source.is_dir():
        shutil.copytree(source, destination, ignore=_ignoreGenerated)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _ignoreGenerated(_directory, names):
    ignored = {"__pycache__", ".pytest_cache"}
    return {name for name in names if name in ignored or name.endswith((".pyc", ".pyo", ".log"))}


def _writeRequirements(platform: str, destination: Path):
    base_lines = _requirementsLines(ROOT / "requirements.txt")
    interface_lines = [
        line
        for line in _requirementsLines(ROOT / "interface" / platform / "requirements.txt")
        if not line.startswith("-r ")
    ]
    destination.write_text(
        "\n".join([*base_lines, *interface_lines]).strip() + "\n",
        encoding="utf-8",
    )


def _requirementsLines(path: Path):
    if not path.exists():
        return []
    lines = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def _writeLauncher(platform: str, destination: Path):
    destination.write_text(LAUNCHERS[platform], encoding="utf-8")


def _writeManifest(plan: BundlePlan):
    manifest = {
        "platform": plan.platform,
        "launcher": plan.launcher_name,
        "included_paths": list(plan.included_paths),
        "requirements": "requirements.txt",
    }
    (plan.output_dir / "BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def _writeArchive(plan: BundlePlan):
    plan.archive_path.parent.mkdir(parents=True, exist_ok=True)
    if plan.archive_path.exists():
        plan.archive_path.unlink()

    with ZipFile(plan.archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in plan.output_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(plan.output_dir.parent))


def main(argv=None):
    """CLI entrypoint for interface builds."""

    parser = argparse.ArgumentParser(description="Build an Aura interface source bundle.")
    parser.add_argument("platform", choices=sorted(LAUNCHERS))
    parser.add_argument("--no-clean", action="store_true", help="Do not remove the previous platform build directory.")
    parser.add_argument("--no-zip", action="store_true", help="Do not create the zip archive.")
    args = parser.parse_args(argv)

    plan = buildInterfaceBundle(args.platform, clean=not args.no_clean, zip_bundle=not args.no_zip)
    print(f"Built {plan.platform} interface bundle: {plan.output_dir}")
    if not args.no_zip:
        print(f"Archive: {plan.archive_path}")


if __name__ == "__main__":
    main()
