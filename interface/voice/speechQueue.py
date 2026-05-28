"""Serialized speech queue for Aura voice output."""

from __future__ import annotations

from queue import Empty, Queue
from threading import Lock
from typing import Any


class SpeechQueue:
    """Queue assistant speech so output never overlaps."""

    def __init__(self, context=None, textToSpeech=None):
        self.context = context
        self.textToSpeech = textToSpeech
        self.logger = context.logger.getChild("Voice.SpeechQueue") if context and getattr(context, "logger", None) else None
        self._queue: Queue[str] = Queue()
        self._lock = Lock()
        self._processing = False
        self._cancelRequested = False
        self.lastResults: list[Any] = []

    def enqueue(self, text: str):
        """Add text to the queue and process it immediately when idle."""

        cleaned = str(text or "").strip()
        if not cleaned or self._cancelRequested:
            return []

        self._queue.put(cleaned)
        if self.logger:
            self.logger.debug("Speech enqueued.")
        return self.processQueue()

    def processQueue(self):
        """Drain the queue in order, one item at a time."""

        with self._lock:
            if self._processing:
                return []
            self._processing = True

        results = []
        try:
            while True:
                try:
                    text = self._queue.get_nowait()
                except Empty:
                    break
                if self._cancelRequested:
                    break

                if self.textToSpeech is None:
                    if self.logger:
                        self.logger.warning("Speech queue has no text-to-speech engine.")
                    continue

                if self.logger:
                    self.logger.debug(f"Processing speech queue item: {text}")
                result = self.textToSpeech.speak(text)
                results.append(result)
        finally:
            with self._lock:
                self._processing = False
                self._cancelRequested = False
            self.lastResults = results

        return results

    def clearQueue(self):
        """Remove all queued speech items without playing them."""

        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                break
        if self.logger:
            self.logger.info("Speech queue cleared.")

    def cancel(self):
        """Cancel queued speech and active playback cooperatively."""

        with self._lock:
            self._cancelRequested = True
        self.clearQueue()
        if self.textToSpeech is not None and hasattr(self.textToSpeech, "cancel"):
            self.textToSpeech.cancel()
