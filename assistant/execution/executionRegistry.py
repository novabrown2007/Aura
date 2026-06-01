"""Registry of executable Aura actions."""

from __future__ import annotations

from typing import Any

from assistant.execution.actions import ActionDefinition


class ExecutionRegistry:
    """Register and look up executable actions by name."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Execution.Registry") if logger else None
        self.entries: dict[str, ActionDefinition] = {}

    def registerAction(self, action: ActionDefinition):
        self.entries[action.actionName] = action
        return action

    def registerTool(self, tool):
        action = ActionDefinition.fromTool(tool)
        return self.registerAction(action)

    def registerTools(self, tools):
        for tool in tools or []:
            self.registerTool(tool)
        return self

    def unregisterAction(self, actionName: str):
        return self.entries.pop(str(actionName), None)

    def getAction(self, actionName: str):
        return self.entries.get(str(actionName))

    def listActions(self) -> list[dict[str, Any]]:
        return [action.asDict() for action in self.entries.values()]

    def refreshFromToolRegistry(self):
        toolRegistry = getattr(self.context, "toolRegistry", None)
        if toolRegistry is None:
            return self
        self.registerTools(toolRegistry.tools.values())
        return self
