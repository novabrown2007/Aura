"""Launch the Windows Aura UI from the project source tree."""

from __future__ import annotations

from interface.windows import AuraWindowsApp
from main import buildRuntimeContext, shutdown, startup


def main():
    """Start the Windows UI with the full Aura runtime context."""

    context = buildRuntimeContext()
    startup(context)
    try:
        AuraWindowsApp(context).run()
    finally:
        shutdown(context)
        if context.logger:
            context.logger.close()


if __name__ == "__main__":
    main()
