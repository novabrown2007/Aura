"""Speech activity states for Aura VAD."""

from __future__ import annotations

from enum import Enum


class VADState(str, Enum):
    """Deterministic speech state names used by the VAD coordinator."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    SPEAKING = "SPEAKING"
    SILENCE_PENDING = "SILENCE_PENDING"
    FINALIZING = "FINALIZING"
    PROCESSING = "PROCESSING"

