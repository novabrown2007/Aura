"""Task lifecycle states."""


class TaskState:
    """Deterministic task states."""

    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"
    PAUSED = "PAUSED"
    TIMED_OUT = "TIMED_OUT"
