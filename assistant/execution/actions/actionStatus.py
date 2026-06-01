"""Execution status labels."""

from __future__ import annotations


class ActionStatus:
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

