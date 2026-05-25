"""Standalone entrypoint for the Aura Developer UI."""

from __future__ import annotations

from auraassistant.core.interface.developerUI.developerApplication import DeveloperApplication


def main():
    """Launch the developer console with a full Aura runtime."""

    raise SystemExit(DeveloperApplication.fromRuntime().run())


if __name__ == "__main__":
    main()

