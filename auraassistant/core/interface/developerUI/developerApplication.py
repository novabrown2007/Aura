"""Application bootstrap for the Aura Developer UI."""

from __future__ import annotations

import sys

from auraassistant.core.interface.developerUI.developerUI import DeveloperUI


class DeveloperApplication:
    """Initialize runtime integrations and manage the PyQt6 UI lifecycle."""

    def __init__(self, context, ownsRuntime: bool = False):
        self.context = context
        self.ownsRuntime = bool(ownsRuntime)
        self.developerUI = DeveloperUI(context)
        self.app = None
        self.window = None
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Application") if logger else None

    @classmethod
    def fromRuntime(cls):
        """Build a full Aura runtime for standalone developer UI launch."""

        from main import buildRuntimeContext, startup

        context = buildRuntimeContext()
        startup(context)
        return cls(context, ownsRuntime=True)

    def run(self) -> int:
        """Run the PyQt6 developer console."""

        try:
            from PyQt6.QtWidgets import QApplication
            from auraassistant.core.interface.developerUI.developerWindow import DeveloperWindow
        except Exception as error:
            message = f"PyQt6 is required for Aura Developer UI: {error}"
            if self.logger:
                self.logger.error(message)
            print(message)
            return 1

        self.developerUI.initialize()
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = DeveloperWindow(self.developerUI)
        self.window.show()
        exitCode = self.app.exec()
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

