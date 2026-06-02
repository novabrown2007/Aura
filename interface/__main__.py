"""Run the default Aura window."""

from __future__ import annotations

import os

from .blank_window import BlankWindowApp


def main():
    """Launch the minimal Aura window."""

    app = BlankWindowApp()
    if os.name == "nt":
        return app.run_in_tray()
    else:
        return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
