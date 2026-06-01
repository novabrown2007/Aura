"""Launch the minimal Aura blank window."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from interface import BlankWindowApp


def main():
    """Start the blank window."""

    BlankWindowApp().run()


if __name__ == "__main__":
    main()
