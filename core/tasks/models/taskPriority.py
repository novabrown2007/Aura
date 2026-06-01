"""Task priority values."""


class TaskPriority:
    """Lightweight priority ordering for queued tasks."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def weight(cls, value) -> int:
        order = {
            cls.CRITICAL: 0,
            cls.HIGH: 1,
            cls.NORMAL: 2,
            cls.LOW: 3,
        }
        normalized = str(value or cls.NORMAL).upper()
        return order.get(normalized, order[cls.NORMAL])
