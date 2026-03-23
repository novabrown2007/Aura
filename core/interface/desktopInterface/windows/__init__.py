"""Windows desktop interface package for Aura.

This package provides the Windows GUI runtime entrypoint and application
class used to run Aura as a desktop executable.
"""

from core.interface.desktopInterface.windows.runAuraWindows import main
from core.interface.desktopInterface.windows.auraWindowsApp import AuraWindowsApp

__all__ = ["AuraWindowsApp", "main"]

