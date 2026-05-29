"""Deterministic speech state transitions for Aura VAD."""

from __future__ import annotations

from threading import RLock
from time import time

from core.voice.vad.models import VADState


class SpeechStateManager:
    """Track the current VAD speech lifecycle state."""

    allowedTransitions = {
        VADState.IDLE: {VADState.LISTENING},
        VADState.LISTENING: {VADState.SPEAKING, VADState.FINALIZING, VADState.IDLE},
        VADState.SPEAKING: {VADState.SILENCE_PENDING, VADState.FINALIZING, VADState.IDLE},
        VADState.SILENCE_PENDING: {VADState.SPEAKING, VADState.FINALIZING, VADState.IDLE},
        VADState.FINALIZING: {VADState.PROCESSING, VADState.IDLE},
        VADState.PROCESSING: {VADState.IDLE, VADState.LISTENING},
    }

    def __init__(self, logger=None):
        self.logger = logger
        self.state = VADState.IDLE
        self.updatedAt = time()
        self.previousState = VADState.IDLE
        self._lock = RLock()

    def transitionTo(self, newState: VADState | str, reason: str = "") -> bool:
        """Move to a new state when the transition is valid."""

        target = newState if isinstance(newState, VADState) else VADState(str(newState))
        with self._lock:
            if target == self.state:
                return True
            if target not in self.allowedTransitions.get(self.state, set()):
                if self.logger:
                    self.logger.warning(f"Ignoring invalid VAD transition {self.state.value}->{target.value}: {reason}")
                return False
            self.previousState = self.state
            self.state = target
            self.updatedAt = time()
            if self.logger:
                self.logger.debug(f"VAD state {self.previousState.value}->{self.state.value}: {reason}")
            return True

    def reset(self, reason: str = "reset"):
        """Return to idle without preserving stale state."""

        with self._lock:
            self.previousState = self.state
            self.state = VADState.IDLE
            self.updatedAt = time()
            if self.logger:
                self.logger.debug(f"VAD state reset: {reason}")

    def snapshot(self) -> dict:
        """Return a serializable state snapshot."""

        with self._lock:
            return {
                "state": self.state.value,
                "previousState": self.previousState.value,
                "updatedAt": self.updatedAt,
            }

