"""Normalize execution results."""

from __future__ import annotations

from typing import Any

from assistant.execution.requests import ExecutionResponse


class ExecutionResultHandler:
    """Convert raw router results into execution response objects."""

    def normalize(self, request, result: Any = None, errors: list[str] | None = None, warnings: list[str] | None = None, status: str = "COMPLETED", metadata: dict | None = None, executionTime: float = 0.0):
        errors = list(errors or [])
        warnings = list(warnings or [])
        payload = result
        if hasattr(result, "asDict"):
            payload = result.asDict()
        elif isinstance(result, dict):
            payload = dict(result)
        return ExecutionResponse(
            requestId=str(getattr(request, "requestId", "") or ""),
            status=status,
            result=payload,
            errors=errors,
            warnings=warnings,
            executionTime=float(executionTime or 0.0),
            metadata=dict(metadata or {}),
        )
