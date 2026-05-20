"""Build the Windows interface bundle."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.interface_build import buildInterfaceBundle  # noqa: E402


if __name__ == "__main__":
    plan = buildInterfaceBundle("windows")
    print(f"Built Windows interface bundle: {plan.output_dir}")
    print(f"Archive: {plan.archive_path}")
