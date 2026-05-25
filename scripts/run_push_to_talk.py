"""Development trigger for Aura's push-to-talk voice loop."""

from __future__ import annotations

from main import buildRuntimeContext, shutdown, startup


def main():
    """Start Aura and run one Enter-to-start, Enter-to-stop voice turn."""

    context = buildRuntimeContext()
    startup(context)
    try:
        manager = getattr(context, "pushToTalkManager", None)
        if manager is None:
            manager = context.voiceManager.pushToTalkManager
        manager.runDevConsoleLoop()
    finally:
        shutdown(context)
        if context.logger:
            context.logger.close()


if __name__ == "__main__":
    main()
