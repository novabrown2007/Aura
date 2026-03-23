"""Text-to-speech service for Aura IO interfaces."""

import threading

try:
    import pyttsx3
except ModuleNotFoundError:  # pragma: no cover - depends on optional runtime package
    pyttsx3 = None


class TextToSpeech:
    """
    Provides speech synthesis for Aura output channels.

    The implementation uses `pyttsx3` when available and falls back gracefully
    when the dependency is missing or disabled via configuration.
    """

    def __init__(self, context):
        """
        Initialize text-to-speech with optional runtime configuration.

        Config keys:
        - io.text_to_speech.enabled (bool, default: False)
        - io.text_to_speech.rate (int, optional)
        - io.text_to_speech.volume (float 0.0-1.0, optional)
        - io.text_to_speech.voice_id (str, optional)
        """

        self.context = context
        self.logger = context.logger.getChild("IO.TTS") if context.logger else None
        self.config = context.config if context else None

        self.enabled = bool(self._cfg("io.text_to_speech.enabled", False))
        self.engine = None
        self._lock = threading.Lock()

        if not self.enabled:
            if self.logger:
                self.logger.info("TextToSpeech disabled by configuration.")
            return

        if pyttsx3 is None:
            self.enabled = False
            if self.logger:
                self.logger.warning(
                    "pyttsx3 is not installed. TextToSpeech disabled."
                )
            return

        try:
            self.engine = pyttsx3.init()
            self._configureEngine()
            if self.logger:
                self.logger.info("TextToSpeech initialized.")
        except Exception as error:  # pragma: no cover - runtime device specific
            self.enabled = False
            self.engine = None
            if self.logger:
                self.logger.error(f"TextToSpeech initialization failed: {error}")

    def _cfg(self, key: str, default=None):
        """Read an optional config value with fallback."""

        if not self.config:
            return default
        return self.config.get(key, default)

    def _configureEngine(self):
        """Apply optional TTS runtime settings to the speech engine."""

        if not self.engine:
            return

        rate = self._cfg("io.text_to_speech.rate", None)
        if rate is not None:
            self.engine.setProperty("rate", int(rate))

        volume = self._cfg("io.text_to_speech.volume", None)
        if volume is not None:
            self.engine.setProperty("volume", float(volume))

        voice_id = self._cfg("io.text_to_speech.voice_id", None)
        if voice_id:
            self.engine.setProperty("voice", str(voice_id))

    def available(self) -> bool:
        """Return whether speech synthesis is currently available."""

        return bool(self.enabled and self.engine is not None)

    def speak(self, text: str):
        """
        Speak text using the configured synthesis engine.

        Args:
            text (str):
                Text to vocalize.
        """

        if not self.available():
            return

        if not text:
            return

        try:
            with self._lock:
                self.engine.say(str(text))
                self.engine.runAndWait()
        except Exception as error:  # pragma: no cover - runtime audio specific
            if self.logger:
                self.logger.warning(f"TTS playback failed: {error}")

    def stop(self):
        """Stop current speech output if the engine is active."""

        if not self.available():
            return
        try:
            self.engine.stop()
        except Exception:  # pragma: no cover - runtime audio specific
            pass

