"""Execution audit logging for Aura governance."""

from __future__ import annotations


class ExecutionAuditLogger:
    """Store a bounded execution audit trail."""

    def __init__(self, context=None, maxEntries: int = 500):
        self.context = context
        self.maxEntries = int(maxEntries)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.Audit") if logger else None
        self.entries: list[dict] = []

    def log(self, request, decision, details: dict | None = None):
        entry = {
            "request": request.asDict() if hasattr(request, "asDict") else dict(request or {}),
            "decision": decision.asDict() if hasattr(decision, "asDict") else dict(decision or {}),
            "details": dict(details or {}),
        }
        self.entries.append(entry)
        if len(self.entries) > self.maxEntries:
            self.entries = self.entries[-self.maxEntries :]
        return entry

    def snapshot(self) -> dict:
        return {"available": True, "entries": list(self.entries[-50:]), "count": len(self.entries)}

