"""Run the default Aura window."""

from __future__ import annotations

import os

from .blank_window import BlankWindowApp


def main():
    """Launch the minimal Aura window."""

    app = BlankWindowApp()
    if os.name == "nt":
        app.run_in_tray()
    else:
        app.run()


if __name__ == "__main__":
    main()
