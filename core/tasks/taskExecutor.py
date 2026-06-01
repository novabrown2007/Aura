"""Centralized task execution adapter."""

from __future__ import annotations

from datetime import datetime
from time import perf_counter

from assistant.execution.requests import ExecutionMetadata, ExecutionRequest

from .models.taskResult import TaskResult
from .models.taskState import TaskState


class TaskExecutor:
    """Run tasks through callable targets or Aura's execution pipeline."""

    def __init__(self, context=None):
        self.context = context

    def executeTask(self, task):
        started = perf_counter()
        task.startedAt = datetime.utcnow().isoformat(timespec="seconds")
        task.state = TaskState.RUNNING
        result = None
        errors: list[str] = []

        try:
            result = self._executePayload(task)
            task.result = result
            task.state = TaskState.COMPLETED
        except Exception as exc:
            task.lastError = str(exc)
            task.state = TaskState.FAILED
            errors.append(str(exc))
        finished = perf_counter()
        task.completedAt = datetime.utcnow().isoformat(timespec="seconds")

        return TaskResult(
            taskId=str(getattr(task, "taskId", "") or getattr(task, "taskName", "")),
            status=task.state,
            result=result,
            errors=errors,
            executionTime=max(0.0, finished - started),
            metadata=dict(getattr(task, "metadata", {}) or {}),
        )

    def _executePayload(self, task):
        executionContext = dict(getattr(task, "executionContext", {}) or {})

        legacyTask = executionContext.get("legacyTask")
        if legacyTask is not None and hasattr(legacyTask, "run"):
            legacyTask.run()
            if getattr(legacyTask, "error", None) is not None:
                raise legacyTask.error
            return getattr(legacyTask, "result", None)

        callableTarget = executionContext.get("callable") or executionContext.get("target")
        if callableTarget is not None and callable(callableTarget):
            args = tuple(executionContext.get("args") or ())
            kwargs = dict(executionContext.get("kwargs") or {})
            return callableTarget(*args, **kwargs)

        requestPayload = executionContext.get("executionRequest") or executionContext.get("actionRequest")
        if requestPayload is not None:
            executionManager = getattr(self.context, "executionManager", None)
            if executionManager is None:
                raise RuntimeError("Execution manager is unavailable.")
            request = self._buildRequest(requestPayload, task)
            response = executionManager.executeRequest(
                request,
                confirmed=bool(executionContext.get("confirmed", False)),
                allowAdmin=bool(executionContext.get("allowAdmin", False)),
                offlineMode=bool(executionContext.get("offlineMode", False)),
            )
            return response

        return executionContext.get("result")

    def _buildRequest(self, payload, task):
        if isinstance(payload, ExecutionRequest):
            return payload

        payload = dict(payload or {})
        metadata = payload.get("metadata")
        if not isinstance(metadata, ExecutionMetadata):
            metadata = ExecutionMetadata.fromDict(metadata) if hasattr(ExecutionMetadata, "fromDict") else ExecutionMetadata()
            if hasattr(metadata, "__dict__") and isinstance(payload.get("metadata"), dict):
                for key, value in payload.get("metadata", {}).items():
                    try:
                        setattr(metadata, key, value)
                    except Exception:
                        pass

        request = ExecutionRequest(
            requestId=str(payload.get("requestId") or ""),
            intent=str(payload.get("intent") or getattr(task, "taskName", "")),
            action=str(payload.get("action") or getattr(task, "taskName", "")),
            parameters=dict(payload.get("parameters") or payload.get("arguments") or {}),
            source=str(payload.get("source") or "TASK"),
            conversationId=str(payload.get("conversationId") or ""),
            requestedBy=str(payload.get("requestedBy") or "task"),
            metadata=metadata,
        )
        return request
