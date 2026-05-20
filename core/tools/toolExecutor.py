"""Safe execution service for deterministic Aura tools."""

from __future__ import annotations

from typing import Any

from core.tools.tool import ToolCategory


class ToolExecutor:
    """Validate and execute tool calls selected by the LLM layer."""

    def __init__(self, context):
        """Bind the executor to the runtime context."""

        self.context = context
        self.logger = context.logger.getChild("ToolExecutor") if context.logger else None

    def executeToolCall(
        self,
        toolName: str,
        arguments: dict[str, Any] | None = None,
        offlineMode: bool = False,
        confirmed: bool = False,
        allowAdmin: bool = False,
    ) -> dict[str, Any]:
        """Validate one tool call and execute it through the owning module."""

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None:
            return self._failure(toolName, "Tool registry is unavailable.")

        tool = registry.getTool(toolName)
        if tool is None:
            return self._failure(toolName, f"Unknown tool: {toolName}")
        if offlineMode and not tool.offlineAllowed:
            return self._failure(toolName, f"Tool is not available in offline mode: {toolName}")
        if tool.category == ToolCategory.ADMIN_ONLY and not allowAdmin:
            return self._failure(toolName, f"Tool requires admin permission: {toolName}", adminOnly=True)
        if (tool.confirmRequired or tool.category == ToolCategory.CONFIRM_REQUIRED) and not confirmed:
            return self._failure(toolName, f"Tool requires confirmation: {toolName}", confirmRequired=True)

        valid, error = tool.validateArguments(arguments or {})
        if not valid:
            return self._failure(toolName, error or "Invalid tool arguments.")

        module = self._resolveModule(tool.module)
        if module is None:
            return self._failure(toolName, f"Module unavailable: {tool.module}")
        if not hasattr(module, tool.method):
            return self._failure(toolName, f"Tool method unavailable: {tool.method}")

        try:
            result = getattr(module, tool.method)(**(arguments or {}))
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Tool execution failed: {toolName}: {error}")
            return self._failure(toolName, str(error))

        if self.logger:
            self.logger.info(f"Executed tool: {toolName}")
        return {"success": True, "toolName": toolName, "result": result}

    def executeToolCalls(
        self,
        toolCalls: list[dict[str, Any]],
        offlineMode: bool = False,
        confirmed: bool = False,
        allowAdmin: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute a sequence of validated tool calls."""

        results = []
        for toolCall in toolCalls:
            if not isinstance(toolCall, dict):
                results.append(self._failure("", "Tool call must be a JSON object."))
                continue
            toolName = str(toolCall.get("toolName") or toolCall.get("tool_name") or "")
            arguments = toolCall.get("arguments") or {}
            results.append(
                self.executeToolCall(
                    toolName,
                    arguments,
                    offlineMode=offlineMode,
                    confirmed=confirmed,
                    allowAdmin=allowAdmin,
                )
            )
        return results

    def validateToolCall(
        self,
        toolName: str,
        arguments: dict[str, Any] | None = None,
        offlineMode: bool = False,
        confirmed: bool = False,
        allowAdmin: bool = False,
    ) -> tuple[bool, str | None]:
        """Validate one tool call without executing it."""

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None:
            return False, "Tool registry is unavailable."

        tool = registry.getTool(toolName)
        if tool is None:
            return False, f"Unknown tool: {toolName}"
        if offlineMode and not tool.offlineAllowed:
            return False, f"Tool is not available in offline mode: {toolName}"
        if tool.category == ToolCategory.ADMIN_ONLY and not allowAdmin:
            return False, f"Tool requires admin permission: {toolName}"
        if (tool.confirmRequired or tool.category == ToolCategory.CONFIRM_REQUIRED) and not confirmed:
            return False, f"Tool requires confirmation: {toolName}"
        return tool.validateArguments(arguments or {})

    def _resolveModule(self, moduleName: str):
        """Resolve a module from context attributes or loaded module map."""

        if hasattr(self.context, moduleName):
            module = getattr(self.context, moduleName)
            if module is not None:
                return module
        return (getattr(self.context, "modules", {}) or {}).get(moduleName)

    @staticmethod
    def _failure(toolName: str, error: str, **extra) -> dict[str, Any]:
        """Build a consistent failed execution result."""

        result = {"success": False, "toolName": toolName, "error": error}
        result.update(extra)
        return result
