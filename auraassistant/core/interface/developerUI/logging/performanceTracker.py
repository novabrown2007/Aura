"""Performance tracking for the Aura Developer UI."""

from __future__ import annotations

from collections import deque
from time import perf_counter


class PerformanceTracker:
    """Track timing for events and subsystem operations."""

    def __init__(self, maxSamples: int = 500):
        self.maxSamples = int(maxSamples)
        self.samples = deque(maxlen=self.maxSamples)
        self.active = {}

    def start(self, name: str):
        """Start timing a named operation."""

        self.active[str(name)] = perf_counter()

    def finish(self, name: str, category: str = "operation") -> float:
        """Finish timing and record the elapsed milliseconds."""

        key = str(name)
        started = self.active.pop(key, None)
        if started is None:
            return 0.0
        durationMs = (perf_counter() - started) * 1000.0
        self.samples.append({"name": key, "category": category, "durationMs": durationMs})
        return durationMs

    def record(self, name: str, durationMs: float, category: str = "operation"):
        """Record an externally measured duration."""

        self.samples.append({"name": str(name), "category": str(category), "durationMs": float(durationMs)})

    def snapshot(self) -> dict:
        """Return aggregate timing state."""

        rows = list(self.samples)
        byCategory = {}
        for row in rows:
            category = row["category"]
            byCategory.setdefault(category, []).append(row["durationMs"])
        aggregates = {}
        for category, values in byCategory.items():
            aggregates[category] = {
                "count": len(values),
                "avgMs": sum(values) / len(values) if values else 0.0,
                "maxMs": max(values) if values else 0.0,
            }
        return {"samples": rows[-50:], "aggregates": aggregates}

