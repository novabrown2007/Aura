"""Run the default Aura window."""

from __future__ import annotations

from .blank_window import BlankWindowApp


def main():
    """Launch the minimal Aura window."""

    BlankWindowApp().run()


if __name__ == "__main__":
    main()
