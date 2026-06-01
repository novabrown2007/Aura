"""Retry coordination for lightweight task execution."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models.retryPolicy import RetryPolicy
from .models.taskState import TaskState


class TaskRetryManager:
    """Apply deterministic retry backoff."""

    def __init__(self, context=None):
        self.context = context

    def shouldRetry(self, task, errors: list[str] | None = None) -> bool:
        policy = self._policy(task)
        if not policy.retryOnFailure:
            return False
        attempts = int(getattr(task, "attempts", 0) or 0)
        return attempts < int(policy.maxRetries or 0)

    def scheduleRetry(self, task, errors: list[str] | None = None):
        policy = self._policy(task)
        attempts = int(getattr(task, "attempts", 0) or 0) + 1
        delay = float(policy.retryDelaySeconds or 0)
        multiplier = float(policy.backoffMultiplier or 1)
        if attempts > 1:
            delay *= multiplier ** (attempts - 1)

        task.attempts = attempts
        task.state = TaskState.RETRYING
        task.lastError = "; ".join(str(item) for item in (errors or []))
        task.scheduledAt = (datetime.utcnow() + timedelta(seconds=delay)).isoformat(timespec="seconds")
        task.nextRunAt = task.scheduledAt
        return task

    @staticmethod
    def _policy(task) -> RetryPolicy:
        policy = getattr(task, "retryPolicy", None)
        if isinstance(policy, RetryPolicy):
            return policy
        return RetryPolicy.fromDict(policy)
