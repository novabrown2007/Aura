"""Application bootstrap for the Aura Developer UI."""

from __future__ import annotations

import os
from pathlib import Path

from interface.developerUI.developerUI import DeveloperUI


class DeveloperApplication:
    """Initialize runtime integrations and manage the Tkinter UI lifecycle."""

    def __init__(self, context, ownsRuntime: bool = False):
        self.context = context
        self.ownsRuntime = bool(ownsRuntime)
        self.developerUI = DeveloperUI(context)
        self.window = None
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Application") if logger else None

    @classmethod
    def fromRuntime(cls):
        """Build a full Aura runtime for standalone developer UI launch."""

        projectRoot = Path(__file__).resolve().parents[2]
        os.chdir(projectRoot)

        from main import buildRuntimeContext, startup

        context = buildRuntimeContext()
        startup(context)
        return cls(context, ownsRuntime=True)

    def run(self) -> int:
        """Run the Tkinter developer console."""

        try:
            from interface.developerUI.developerWindow import DeveloperWindow
        except Exception as error:
            message = f"Tkinter is required for Aura Developer UI: {error}"
            if self.logger:
                self.logger.error(message)
            print(message)
            return 1

        self.developerUI.initialize()
        self.window = DeveloperWindow(self.developerUI)
        exitCode = self.window.run()
        self.shutdown()
        return int(exitCode)

    def shutdown(self):
        """Shutdown UI and optionally owned Aura runtime."""

        try:
            self.developerUI.shutdown()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Developer UI shutdown failed: {error}")

        if self.ownsRuntime:
            try:
                from main import shutdown

                shutdown(self.context)
            finally:
                logger = getattr(self.context, "logger", None)
                if logger:
                    logger.close()
