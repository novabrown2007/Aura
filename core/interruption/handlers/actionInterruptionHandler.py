"""Action/module interruption handler."""

from __future__ import annotations


class ActionInterruptionHandler:
    """Cancel queued or pending runtime actions when subsystems expose hooks."""

    systemName = "action"

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Interruption.Action") if logger else None

    def cancel(self, interruptionContext) -> list[str]:
        """Cancel action-oriented managers cooperatively."""

        cancelled = []
        for name in ("taskManager", "scheduler", "autonomousTasks", "toolOrchestrator"):
            target = getattr(self.context, name, None)
            if target is None or not hasattr(target, "cancelPending"):
                continue
            try:
                target.cancelPending()
                cancelled.append(name)
            except Exception as error:
                interruptionContext.markFailed(name, str(error))
        return cancelled

