"""Canonical Aura event names emitted by the wake word subsystem."""


class WakeWordEvents:
    """String constants for wake word event bus integration."""

    LISTENING_STARTED = "wakeword.listening.started"
    LISTENING_STOPPED = "wakeword.listening.stopped"
    DETECTED = "wakeword.detected"
    COOLDOWN_STARTED = "wakeword.cooldown.started"
    COOLDOWN_FINISHED = "wakeword.cooldown.finished"
    ERROR = "wakeword.error"
