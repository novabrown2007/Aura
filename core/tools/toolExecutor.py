"""Safe execution service for deterministic Aura tools."""

from __future__ import annotations

from typing import Any

from core.tools.tool import ToolCategory
from assistant.safety.models import ExecutionContext, ExecutionRequest


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

        observability = getattr(self.context, "observability", None)
        if observability is not None:
            observability.recordTrace("tool", toolName, status="started")

        executionManager = getattr(self.context, "executionManager", None)
        if executionManager is None:
            try:
                from assistant.execution import ExecutionManager

                executionManager = ExecutionManager(self.context)
            except Exception:
                executionManager = None
        if executionManager is not None and hasattr(executionManager, "executeToolCall"):
            try:
                result = executionManager.executeToolCall(
                    toolName,
                    arguments or {},
                    offlineMode=offlineMode,
                    confirmed=confirmed,
                    allowAdmin=allowAdmin,
                )
                self._recordToolTrace(observability, toolName, result)
                return result
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Execution manager failed for {toolName}: {error}")

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None:
            result = self._failure(toolName, "Tool registry is unavailable.")
            self._recordToolTrace(observability, toolName, result)
            return result

        tool = registry.getTool(toolName)
        if tool is None:
            result = self._failure(toolName, f"Unknown tool: {toolName}")
            self._recordToolTrace(observability, toolName, result)
            return result

        request = ExecutionRequest(
            source="tool",
            module=str(tool.module or ""),
            action=str(tool.name or toolName),
            parameters=dict(arguments or {}),
            executionContext=ExecutionContext(
                interface={"offlineMode": bool(offlineMode)},
                metadata={"tool": tool.asDict() if hasattr(tool, "asDict") else {}},
            ),
            requestedBy="assistant",
            priority="NORMAL",
            metadata={"confirmed": bool(confirmed), "allowAdmin": bool(allowAdmin)},
        )

        safetyGate = getattr(self.context, "executionGuard", None) or getattr(self.context, "safetyManager", None)
        if safetyGate is not None and hasattr(safetyGate, "canExecute"):
            decision = safetyGate.canExecute(request, tool=tool, confirmed=confirmed, allowAdmin=allowAdmin)
            if not decision.canExecute():
                result = self._failure(
                    toolName,
                    decision.reason or f"Execution blocked: {decision.decision}",
                    decision=decision.asDict() if hasattr(decision, "asDict") else {},
                    requiresConfirmation=bool(getattr(decision, "requiresConfirmation", False)),
                    cooldownRemaining=float(getattr(decision, "cooldownRemaining", 0.0) or 0.0),
                )
                self._recordToolTrace(observability, toolName, result)
                return result

        if offlineMode and not tool.offlineAllowed:
            result = self._failure(toolName, f"Tool is not available in offline mode: {toolName}")
            self._recordToolTrace(observability, toolName, result)
            return result
        if self._toolCategory(tool) == "ADMIN_ONLY" and not allowAdmin:
            result = self._failure(toolName, f"Tool requires admin permission: {toolName}", adminOnly=True)
            self._recordToolTrace(observability, toolName, result)
            return result
        if (tool.confirmRequired or self._toolCategory(tool) == "CONFIRM_REQUIRED") and not confirmed:
            result = self._failure(toolName, f"Tool requires confirmation: {toolName}", confirmRequired=True)
            self._recordToolTrace(observability, toolName, result)
            return result

        valid, error = tool.validateArguments(arguments or {})
        if not valid:
            result = self._failure(toolName, error or "Invalid tool arguments.")
            self._recordToolTrace(observability, toolName, result)
            return result

        module = self._resolveModule(tool.module)
        if module is None:
            result = self._failure(toolName, f"Module unavailable: {tool.module}")
            self._recordToolTrace(observability, toolName, result)
            return result
        if not hasattr(module, tool.method):
            result = self._failure(toolName, f"Tool method unavailable: {tool.method}")
            self._recordToolTrace(observability, toolName, result)
            return result

        try:
            result = getattr(module, tool.method)(**(arguments or {}))
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Tool execution failed: {toolName}: {error}")
            result = self._failure(toolName, str(error))
            self._recordToolTrace(observability, toolName, result)
            safetyManager = getattr(self.context, "safetyManager", None)
            if safetyManager is not None and hasattr(safetyManager, "_emit"):
                try:
                    safetyManager._emit("execution.failed", {"toolName": toolName, "error": str(error)})
                except Exception:
                    pass
            return result

        if self.logger:
            self.logger.info(f"Executed tool: {toolName}")
        result = {"success": True, "toolName": toolName, "result": result}
        safetyManager = getattr(self.context, "safetyManager", None)
        if safetyManager is not None and hasattr(safetyManager, "_emit"):
            try:
                safetyManager._emit("execution.completed", {"toolName": toolName, "result": result})
            except Exception:
                pass
        self._recordToolTrace(observability, toolName, result)
        return result

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
        if self._toolCategory(tool) == "ADMIN_ONLY" and not allowAdmin:
            return False, f"Tool requires admin permission: {toolName}"
        if (tool.confirmRequired or self._toolCategory(tool) == "CONFIRM_REQUIRED") and not confirmed:
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
    def _recordToolTrace(observability, toolName: str, result: dict[str, Any]):
        """Record a final tool execution trace."""

        if observability is None:
            return
        observability.recordTrace(
            "tool",
            toolName,
            status="completed" if result.get("success") else "failed",
            details={key: value for key, value in result.items() if key != "result"},
        )

    @staticmethod
    def _failure(toolName: str, error: str, **extra) -> dict[str, Any]:
        """Build a consistent failed execution result."""

        result = {"success": False, "toolName": toolName, "error": error}
        result.update(extra)
        return result

    @staticmethod
    def _toolCategory(tool) -> str:
        category = getattr(tool, "category", "")
        if hasattr(category, "value"):
            category = category.value
        return str(category or "").upper()
