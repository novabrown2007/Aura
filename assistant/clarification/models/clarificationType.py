"""Clarification type enumeration."""

from __future__ import annotations

from enum import Enum


class ClarificationType(str, Enum):
    """Types of clarification Aura can request."""

    MISSING_PARAMETER = "MISSING_PARAMETER"
    MULTIPLE_OPTIONS = "MULTIPLE_OPTIONS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CONFIRMATION = "CONFIRMATION"
    TARGET_SELECTION = "TARGET_SELECTION"
    TIME_SELECTION = "TIME_SELECTION"
    LOCATION_SELECTION = "LOCATION_SELECTION"
    ACCOUNT_SELECTION = "ACCOUNT_SELECTION"
