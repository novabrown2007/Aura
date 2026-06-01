"""Execution lifecycle event names."""

from __future__ import annotations


EXECUTION_EVENTS = (
    "execution.requested",
    "execution.validated",
    "execution.authorized",
    "execution.started",
    "execution.completed",
    "execution.failed",
    "execution.denied",
)
