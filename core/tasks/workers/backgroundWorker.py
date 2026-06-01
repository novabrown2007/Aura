"""Background worker wrapper for recurring monitoring work."""

from __future__ import annotations

from ..taskWorker import TaskWorker


class BackgroundWorker(TaskWorker):
    """Background worker alias used by the task system architecture."""

    pass
