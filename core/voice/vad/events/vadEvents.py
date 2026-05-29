"""Canonical event names emitted by Aura's VAD system."""

from __future__ import annotations


class VADEvents:
    """Voice activity detection event constants."""

    STARTED = "vad.started"
    SPEECH_DETECTED = "vad.speech.detected"
    SILENCE_DETECTED = "vad.silence.detected"
    SPEECH_COMPLETED = "vad.speech.completed"
    FINALIZING = "vad.finalizing"
    TIMEOUT = "vad.timeout"
    ERROR = "vad.error"

