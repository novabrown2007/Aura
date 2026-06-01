"""Event bus bridge for task lifecycle events."""

from __future__ import annotations


class TaskEventHandler:
    """Subscribe Aura events to task orchestration actions."""

    def __init__(self, context=None, taskManager=None):
        self.context = context
        self.taskManager = taskManager
        self._subscribed = False

    def subscribe(self):
        if self._subscribed:
            return self
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return self
        eventManager.subscribe("system.started", self._handleSystemStarted)
        eventManager.subscribe("system.shutdown", self._handleSystemShutdown)
        eventManager.subscribe("execution.completed", self._handleExecutionCompleted)
        eventManager.subscribe("execution.failed", self._handleExecutionFailed)
        self._subscribed = True
        return self

    def unsubscribe(self):
        self._subscribed = False

    def _handleSystemStarted(self, event):
        if self.taskManager is not None:
            self.taskManager.start()

    def _handleSystemShutdown(self, event):
        if self.taskManager is not None:
            self.taskManager.stop()

    def _handleExecutionCompleted(self, event):
        return event

    def _handleExecutionFailed(self, event):
        return event
