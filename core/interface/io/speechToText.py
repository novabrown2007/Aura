"""Speech-to-text service for Aura IO interfaces."""

try:
    import speech_recognition as sr
except ModuleNotFoundError:  # pragma: no cover - depends on optional runtime package
    sr = None


class SpeechToText:
    """
    Provides microphone and file-based speech recognition for Aura input flows.

    The implementation uses `speech_recognition` when available and disables
    itself gracefully otherwise.
    """

    def __init__(self, context):
        """
        Initialize speech recognition with optional runtime configuration.

        Config keys:
        - io.speech_to_text.enabled (bool, default: False)
        - io.speech_to_text.timeout (int/float, default: 5)
        - io.speech_to_text.phrase_time_limit (int/float, default: 10)
        - io.speech_to_text.provider (str: "google"|"sphinx", default: "google")
        """

        self.context = context
        self.logger = context.logger.getChild("IO.STT") if context.logger else None
        self.config = context.config if context else None

        self.enabled = bool(self._cfg("io.speech_to_text.enabled", False))
        self.timeout = self._cfg("io.speech_to_text.timeout", 5)
        self.phrase_time_limit = self._cfg("io.speech_to_text.phrase_time_limit", 10)
        self.provider = str(self._cfg("io.speech_to_text.provider", "google")).lower()

        self.recognizer = None

        if not self.enabled:
            if self.logger:
                self.logger.info("SpeechToText disabled by configuration.")
            return

        if sr is None:
            self.enabled = False
            if self.logger:
                self.logger.warning(
                    "speech_recognition is not installed. SpeechToText disabled."
                )
            return

        self.recognizer = sr.Recognizer()
        if self.logger:
            self.logger.info("SpeechToText initialized.")

    def _cfg(self, key: str, default=None):
        """Read an optional config value with fallback."""

        if not self.config:
            return default
        return self.config.get(key, default)

    def available(self) -> bool:
        """Return whether speech recognition is currently available."""

        return bool(self.enabled and self.recognizer is not None)

    def listenOnce(self):
        """
        Capture one utterance from the microphone and transcribe it.

        Returns:
            str | None:
                Transcribed text, or None on timeout/failure/unavailable service.
        """

        if not self.available():
            return None

        try:
            with sr.Microphone() as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=float(self.timeout),
                    phrase_time_limit=float(self.phrase_time_limit),
                )
            return self._recognize(audio)
        except Exception as error:  # pragma: no cover - runtime device specific
            if self.logger:
                self.logger.warning(f"Microphone transcription failed: {error}")
            return None

    def transcribeAudioFile(self, path: str):
        """
        Transcribe speech from an audio file.

        Args:
            path (str):
                Path to WAV/AIFF/FLAC-compatible audio file.

        Returns:
            str | None:
                Transcribed text, or None on failure.
        """

        if not self.available():
            return None

        try:
            with sr.AudioFile(path) as source:
                audio = self.recognizer.record(source)
            return self._recognize(audio)
        except Exception as error:  # pragma: no cover - runtime codec specific
            if self.logger:
                self.logger.warning(f"Audio-file transcription failed: {error}")
            return None

    def _recognize(self, audio):
        """Recognize text from an `speech_recognition.AudioData` instance."""

        try:
            if self.provider == "sphinx":
                return self.recognizer.recognize_sphinx(audio)
            return self.recognizer.recognize_google(audio)
        except Exception:
            return None

