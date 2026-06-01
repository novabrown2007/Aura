"""Clarification lifecycle state enumeration."""

from __future__ import annotations

from enum import Enum


class ClarificationState(str, Enum):
    """Lifecycle state for a clarification session."""

    PENDING = "PENDING"
    WAITING_FOR_RESPONSE = "WAITING_FOR_RESPONSE"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    FAILED = "FAILED"
