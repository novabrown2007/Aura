"""Interface-specific test package for Aura."""

from pathlib import Path


def load_tests(loader, standard_tests, pattern):
    """Allow `tests.interfaceTests` to load all platform interface tests."""

    package_dir = Path(__file__).parent
    project_root = package_dir.parents[1]
    return loader.discover(
        start_dir=str(package_dir),
        pattern=pattern or "test_*.py",
        top_level_dir=str(project_root),
    )
