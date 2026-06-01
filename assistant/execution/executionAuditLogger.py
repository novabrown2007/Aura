"""Execution audit logging."""

from __future__ import annotations

from time import time


class ExecutionAuditLogger:
    """Collect an execution audit trail."""

    def __init__(self, context=None):
        self.context = context
        self.records: list[dict] = []
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Execution.Audit") if logger else None

    def log(self, request, response, details: dict | None = None):
        record = {
            "timestamp": time(),
            "request": request.asDict() if hasattr(request, "asDict") else dict(request or {}),
            "response": response.asDict() if hasattr(response, "asDict") else dict(response or {}),
            "details": dict(details or {}),
        }
        self.records.append(record)
        if self.logger:
            self.logger.info(f"Execution audit: {record['response'].get('status', '')} {record['request'].get('action', '')}")
        return record

    def snapshot(self):
        return {"available": True, "count": len(self.records)}
