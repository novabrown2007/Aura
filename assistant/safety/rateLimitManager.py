"""Execution rate limiting for Aura."""

from __future__ import annotations

from collections import defaultdict, deque
from time import time


class RateLimitManager:
    """Prevent action spam and automation loops."""

    def __init__(self, context=None, maxExecutionsPerMinute: int = 20):
        self.context = context
        self.maxExecutionsPerMinute = int(maxExecutionsPerMinute)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.RateLimit") if logger else None
        self._executions: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, request):
        """Return whether an execution may proceed."""

        if self.maxExecutionsPerMinute <= 0:
            return True, 0.0
        key = self._key(request)
        window = self._executions[key]
        now = time()
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= self.maxExecutionsPerMinute:
            cooldown = max(0.0, 60.0 - (now - window[0]))
            return False, cooldown
        window.append(now)
        return True, 0.0

    def snapshot(self) -> dict:
        return {
            "maxExecutionsPerMinute": self.maxExecutionsPerMinute,
            "activeKeys": {key: len(window) for key, window in self._executions.items()},
        }

    @staticmethod
    def _key(request) -> str:
        return ":".join(
            str(part or "")
            for part in (
                getattr(request, "source", ""),
                getattr(request, "module", ""),
                getattr(request, "action", ""),
                getattr(request, "requestedBy", ""),
            )
        )

