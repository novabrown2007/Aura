"""Local Piper TTS synthesis support for Aura."""

from __future__ import annotations

import tempfile
import time
import wave
from pathlib import Path
from threading import Lock
from threading import Event

from .audioPlayer import AudioPlayer
from .models.speechResult import SpeechResult


class TextToSpeech:
    """Generate and play local speech using cached Piper voices."""

    def __init__(
        self,
        context=None,
        modelPath: str = "en_US-lessac-medium",
        outputDirectory: str = "temp/voice",
        playbackEnabled: bool = True,
        sampleRate: int = 22050,
        autoDownloadModel: bool = True,
    ):
        self.context = context
        self.logger = context.logger.getChild("Voice.TTS") if context and getattr(context, "logger", None) else None
        self.modelPath = str(modelPath)
        self.outputDirectory = str(outputDirectory)
        self.playbackEnabled = bool(playbackEnabled)
        self.sampleRate = int(sampleRate)
        self.autoDownloadModel = bool(autoDownloadModel)
        self.audioPlayer = AudioPlayer(context)
        self.model = None
        self.initialized = False
        self.lastResult = SpeechResult()
        self.lastError = ""
        self._lock = Lock()
        self._cancelEvent = Event()
        self._generatedAudioPaths: list[Path] = []

    def initialize(self):
        """Load the Piper voice model once and keep it cached."""

        if self.model is not None:
            return self.model

        with self._lock:
            if self.model is not None:
                return self.model

            start = time.perf_counter()
            try:
                PiperVoice = self._importPiperVoice()
            except Exception as error:
                self.lastError = f"Piper TTS is unavailable: {error}"
                self.initialized = False
                if self.logger:
                    self.logger.error(self.lastError)
                return None

            modelPath = self._resolveModelPath(self.modelPath)
            if modelPath is None and self.autoDownloadModel:
                self._downloadVoiceModel(self.modelPath)
                modelPath = self._resolveModelPath(self.modelPath)
            if modelPath is None:
                searched = ", ".join(str(path) for path in self._modelPathCandidates(self.modelPath))
                self.lastError = (
                    f"Voice model not found: {self.modelPath}. "
                    f"Searched: {searched}. Set voice.TTS.voiceModelPath to a local Piper .onnx file "
                    "or disable voice.pushToTalk.pushToTalkAutoSpeak until a voice model is installed."
                )
                self.initialized = False
                if self.logger:
                    self.logger.error(self.lastError)
                return None

            try:
                self.model = PiperVoice.load(str(modelPath))
                self.initialized = True
                elapsed = time.perf_counter() - start
                if self.logger:
                    self.logger.info(f"Loaded Piper voice '{modelPath}' in {elapsed:.3f}s")
                return self.model
            except Exception as error:
                self.model = None
                self.initialized = False
                self.lastError = str(error)
                if self.logger:
                    self.logger.error(f"Failed to load Piper voice model: {error}")
                return None

    def speak(self, text: str):
        """Generate speech and optionally play it back immediately."""

        result = self.generateSpeech(text)
        if not result.success:
            return result

        try:
            if self.playbackEnabled:
                playbackDuration = self.audioPlayer.playAudio(result.audioPath)
                result.playbackDuration = playbackDuration
                if self.logger:
                    self.logger.info(f"Playback duration: {playbackDuration:.3f}s")
        except Exception as error:
            result.success = False
            result.errorMessage = str(error)
            if self.logger:
                self.logger.error(f"Playback failed: {error}")
        finally:
            self._cleanupGeneratedAudio(result.audioPath)

        self.lastResult = result
        return result

    def generateSpeech(self, text: str):
        """Synthesise text into a temporary WAV file."""

        cleaned = str(text or "").strip()
        if not cleaned:
            result = SpeechResult(success=False, errorMessage="Empty speech text.")
            self.lastResult = result
            return result

        # A previous interruption should not permanently suppress later speech.
        self._cancelEvent.clear()

        model = self.initialize()
        if model is None:
            result = SpeechResult(success=False, errorMessage=self.lastError or "Piper voice model is unavailable.")
            self.lastResult = result
            return result

        start = time.perf_counter()
        try:
            self._registerSpeechOperation(cleaned)
            outputPath = self._createOutputPath()
            with wave.open(str(outputPath), "wb") as audioFile:
                if self._cancelEvent.is_set():
                    raise RuntimeError("Speech cancelled.")
                model.synthesize_wav(cleaned, audioFile)
            if self._cancelEvent.is_set():
                raise RuntimeError("Speech cancelled.")

            generationTime = time.perf_counter() - start
            if self.logger:
                self.logger.info(f"Synthesized speech in {generationTime:.3f}s -> {outputPath}")
                self.logger.debug(f"Synthesized text: {cleaned}")

            result = SpeechResult(
                success=True,
                audioPath=str(outputPath),
                generationTime=generationTime,
                playbackDuration=0.0,
                errorMessage="",
            )
            self._generatedAudioPaths.append(outputPath)
            self.lastResult = result
            return result
        except Exception as error:
            generationTime = time.perf_counter() - start
            self.lastError = str(error)
            if self.logger:
                self.logger.error(f"Speech synthesis failed: {error}")
            result = SpeechResult(
                success=False,
                audioPath="",
                generationTime=generationTime,
                playbackDuration=0.0,
                errorMessage=self.lastError,
            )
            self.lastResult = result
            return result
        finally:
            self._completeSpeechOperation()

    def shutdown(self):
        """Release cached model references and clean temp audio files."""

        if self.logger:
            self.logger.info("Shutting down text-to-speech cache.")
        try:
            self.audioPlayer.stopAudio()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Audio player shutdown failed: {error}")
        self._cleanupGeneratedAudio()
        self.model = None
        self.initialized = False

    def cancel(self):
        """Cancel active speech generation/playback and clean queued audio."""

        self._cancelEvent.set()
        try:
            self.audioPlayer.stopAudio()
        except Exception:
            pass
        self._cleanupGeneratedAudio()

    def _resolveModelPath(self, value: str) -> Path | None:
        """Find a local Piper model path from a configurable input."""

        for candidate in self._modelPathCandidates(value):
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()

        return None

    def _modelPathCandidates(self, value: str) -> list[Path]:
        """Return local Piper model locations to check for a configured value."""

        raw = Path(str(value or "").strip())
        candidates: list[Path] = []

        if raw.exists():
            candidates.append(raw)
        if not raw.suffix:
            candidates.append(raw.with_suffix(".onnx"))
        if not raw.is_absolute():
            candidates.append(Path.cwd() / raw)
            if not raw.suffix:
                candidates.append(Path.cwd() / raw.with_suffix(".onnx"))
            candidates.append(Path("voices") / raw)
            if not raw.suffix:
                candidates.append(Path("voices") / raw.with_suffix(".onnx"))
            candidates.append(Path("voice_models") / raw)
            if not raw.suffix:
                candidates.append(Path("voice_models") / raw.with_suffix(".onnx"))

        seen = set()
        uniqueCandidates: list[Path] = []
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                uniqueCandidates.append(candidate)
        return uniqueCandidates

    def _downloadVoiceModel(self, value: str):
        """Download a named Piper voice model and config when missing."""

        voiceName = self._voiceNameFromModelPath(value)
        if not voiceName:
            return

        downloadDirectory = self._voiceDownloadDirectory(value)
        try:
            from piper.download_voices import download_voice
        except Exception as error:
            self.lastError = f"Piper voice downloader is unavailable: {error}"
            if self.logger:
                self.logger.error(self.lastError)
            return

        try:
            downloadDirectory.mkdir(parents=True, exist_ok=True)
            if self.logger:
                self.logger.info(f"Downloading Piper voice model '{voiceName}' to {downloadDirectory}")
            download_voice(voiceName, downloadDirectory)
        except Exception as error:
            self.lastError = f"Piper voice model download failed for {voiceName}: {error}"
            if self.logger:
                self.logger.error(self.lastError)

    @staticmethod
    def _voiceNameFromModelPath(value: str) -> str:
        """Return a Piper voice name such as en_US-lessac-medium."""

        raw = str(value or "").strip()
        if not raw:
            return ""
        path = Path(raw)
        if path.suffix == ".json":
            path = path.with_suffix("")
        if path.suffix == ".onnx":
            return path.stem
        return path.name

    @staticmethod
    def _voiceDownloadDirectory(value: str) -> Path:
        """Return where auto-downloaded Piper voices should live."""

        raw = Path(str(value or "").strip())
        if raw.parent != Path("."):
            return raw.parent
        return Path("voices")

    def _createOutputPath(self) -> Path:
        """Create a temp WAV path inside the configured output directory."""

        outputDir = Path(self.outputDirectory).expanduser()
        outputDir.mkdir(parents=True, exist_ok=True)
        tempFile = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=str(outputDir))
        tempFile.close()
        return Path(tempFile.name)

    def _cleanupGeneratedAudio(self, path: str | None = None):
        """Remove generated temp audio after playback or shutdown."""

        paths = []
        if path:
            paths.append(Path(path))
        paths.extend(self._generatedAudioPaths)
        self._generatedAudioPaths = []

        for item in paths:
            try:
                item.unlink(missing_ok=True)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Failed to remove generated speech file {item}: {error}")

    def _registerSpeechOperation(self, text: str):
        registry = getattr(self.context, "interruptionRegistry", None)
        if registry is None:
            return
        try:
            registry.registerOperation(
                "tts.synthesis",
                "voice",
                "tts",
                cancelHandler=lambda _context: self.cancel(),
                metadata={"textPreview": str(text or "")[:160]},
            )
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Failed to register TTS interruption operation: {error}")

    def _completeSpeechOperation(self):
        registry = getattr(self.context, "interruptionRegistry", None)
        if registry is None:
            return
        try:
            registry.completeOperation("tts.synthesis")
        except Exception:
            pass

    @staticmethod
    def _importPiperVoice():
        """Import PiperVoice with a compatibility fallback."""

        try:
            from piper.voice import PiperVoice
            return PiperVoice
        except Exception:
            from piper import PiperVoice
            return PiperVoice
