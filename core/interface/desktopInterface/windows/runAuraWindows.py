"""Windows runtime entrypoint for launching Aura's Tk shell."""

import ctypes

from core.interface.desktopInterface.windows.auraWindowsApp import AuraWindowsApp
from core.interface.desktopInterface.windows.errorDialog import showStandaloneErrorPopup
from core.interface.desktopInterface.windows.windowsRuntimeBootstrap import (
    createRuntimeContext,
    shutdown,
    startup,
)

WINDOWS_APP_ID = "NovaBrown.Aura.Windows"


def _setWindowsAppId():
    """Set a stable Windows AppUserModelID when running on Windows."""

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        return


def main():
    """Create runtime context, launch the app, and ensure clean shutdown."""

    context = None
    try:
        _setWindowsAppId()
        context = createRuntimeContext()
        startup(context)
        app = AuraWindowsApp(context)
        app.run()
    except Exception as error:
        showStandaloneErrorPopup(str(error))
    finally:
        if context is not None:
            shutdown(context)


if __name__ == "__main__":
    main()
