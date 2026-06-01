"""Canonical task event names."""


class TaskEvents:
    """Event names emitted by the async task system."""

    CREATED = "task.created"
    SCHEDULED = "task.scheduled"
    STARTED = "task.started"
    COMPLETED = "task.completed"
    FAILED = "task.failed"
    CANCELLED = "task.cancelled"
    RETRYING = "task.retrying"
