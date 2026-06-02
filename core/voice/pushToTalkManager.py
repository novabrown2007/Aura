"""Push-to-talk microphone capture and transcription for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter
from typing import Any


@dataclass
class SpeechResult:
    """Normalized result for one captured voice turn."""

    success: bool = False
    errorMessage: str = ""
    transcribedText: str = ""
    assistantResponse: str = ""
    source: str = ""
    audioDurationSeconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "success": bool(self.success),
            "errorMessage": self.errorMessage,
            "transcribedText": self.transcribedText,
            "assistantResponse": self.assistantResponse,
            "source": self.source,
            "audioDurationSeconds": float(self.audioDurationSeconds),
            "metadata": dict(self.metadata or {}),
        }


@dataclass
class PushToTalkResult:
    """Result returned by the push-to-talk capture pipeline."""

    success: bool = False
    errorMessage: str = ""
    transcribedText: str = ""
    assistantResponse: str = ""
    source: str = ""
    audioDurationSeconds: float = 0.0
    speech: SpeechResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "success": bool(self.success),
            "errorMessage": self.errorMessage,
            "transcribedText": self.transcribedText,
            "assistantResponse": self.assistantResponse,
            "source": self.source,
            "audioDurationSeconds": float(self.audioDurationSeconds),
            "speech": self.speech.asDict() if self.speech is not None and hasattr(self.speech, "asDict") else None,
            "metadata": dict(self.metadata or {}),
        }


class PushToTalkManager:
    """Capture microphone audio until release, then transcribe it."""

    def __init__(
        self,
        context=None,
        vadManager=None,
        voiceManager=None,
        streamFactory=None,
        transcriberFactory=None,
    ):
        self.context = context
        self.vadManager = vadManager or getattr(context, "vadManager", None)
        self.voiceManager = voiceManager or getattr(context, "voiceManager", None)
        self._streamFactory = streamFactory
        self._transcriberFactory = transcriberFactory
        self.logger = context.logger.getChild("Voice.PushToTalk") if context and getattr(context, "logger", None) else None
        self.enabled = self._configBool("voice.pushToTalk.enabled", True)
        self.autoSpeak = self._configBool("voice.pushToTalk.pushToTalkAutoSpeak", True)
        self.tempAudioDirectory = str(self._configValue("voice.pushToTalk.pushToTalkTempAudioDirectory", "temp/push_to_talk"))
        self.sampleRate = int(self._configValue("voice.STT.sampleRate", 16000))
        self.modelName = str(self._configValue("voice.STT.model", "small.en"))
        self.device = str(self._configValue("voice.STT.device", "cpu"))
        self.computeType = str(self._configValue("voice.STT.computeType", "int8"))
        self.microphoneDevice = self._configValue(
            "voice.wakeWord.wakeWordMicrophoneDevice",
            self._configValue("voice.alwaysActive.wakeWordMicrophoneDevice", None),
        )
        self.vadControlled = bool(getattr(self.vadManager, "enabled", False))
        self.lastError = ""
        self.lastResult = PushToTalkResult(source="idle")
        self._lock = Lock()
        self._capturing = False
        self._captureStart = 0.0
        self._activeSource = "push_to_talk"
        self._frames: list[Any] = []
        self._stream = None
        self._numpy = None
        self._sounddevice = None
        self._transcriber = None
        self._transcriberError = ""

        if self.context is not None:
            self.context.pushToTalkManager = self

        if self.logger:
            self.logger.info(
                "Push-to-talk manager created "
                f"(enabled={self.enabled}, sampleRate={self.sampleRate}, device={self.microphoneDevice!r}, vadControlled={self.vadControlled})."
            )

    def startCapture(self, source: str = "push_to_talk") -> bool:
        """Open the microphone and begin buffering audio."""

        if not self.enabled:
            self.lastError = "Push-to-talk is disabled by configuration."
            return False

        with self._lock:
            if self._capturing:
                return True

            self._frames = []
            self.lastError = ""
            self._activeSource = str(source or "push_to_talk")
            self._captureStart = perf_counter()

            try:
                self._openStream()
                if self.vadManager is not None and getattr(self.vadManager, "enabled", False):
                    self.vadManager.startSession(source=self._activeSource)
                self._capturing = True
                self._emit("voice.capture.started", {"source": self._activeSource})
                if self.logger:
                    self.logger.info(f"Push-to-talk capture started from source={self._activeSource}.")
                return True
            except Exception as error:
                self.lastError = str(error)
                self._cleanupStream()
                self._cancelVadSession("capture failed")
                self._capturing = False
                if self.logger:
                    self.logger.error(f"Push-to-talk capture could not start: {error}")
                return False

    def stopAndProcess(self) -> PushToTalkResult:
        """Stop capture, transcribe the recorded audio, and dispatch the transcript."""

        with self._lock:
            if not self._capturing and not self._frames:
                result = PushToTalkResult(
                    success=False,
                    errorMessage=self.lastError or "No push-to-talk capture is active.",
                    source=self._activeSource,
                    speech=SpeechResult(success=False, errorMessage=self.lastError or "No capture is active.", source=self._activeSource),
                )
                self.lastResult = result
                return result

            frames = list(self._frames)
            source = self._activeSource
            start = self._captureStart
            self._capturing = False
            self._captureStart = 0.0
            self._frames = []

        self._cleanupStream()

        vadSession = None
        if self.vadManager is not None and hasattr(self.vadManager, "finalizeSession"):
            try:
                vadSession = self.vadManager.finalizeSession(reason="push-to-talk stop")
            except Exception as error:
                self.lastError = str(error)
                if self.logger:
                    self.logger.warning(f"VAD session finalization failed: {error}")

        if not frames:
            result = PushToTalkResult(
                success=False,
                errorMessage="No audio was captured.",
                source=source,
                speech=SpeechResult(success=False, errorMessage="No audio was captured.", source=source),
            )
            self.lastResult = result
            self._finishVadProcessing()
            return result

        try:
            audio = self._combineFrames(frames)
            transcribedText = self._transcribe(audio)
            audioDurationSeconds = max(0.0, perf_counter() - start) if start > 0 else 0.0
            if not transcribedText:
                result = PushToTalkResult(
                    success=False,
                    errorMessage="No speech was recognized.",
                    transcribedText="",
                    assistantResponse="",
                    source=source,
                    audioDurationSeconds=audioDurationSeconds,
                    speech=SpeechResult(
                        success=False,
                        errorMessage="No speech was recognized.",
                        source=source,
                        audioDurationSeconds=audioDurationSeconds,
                    ),
                    metadata={"vadSession": vadSession.snapshot() if vadSession is not None and hasattr(vadSession, "snapshot") else {}},
                )
                self.lastResult = result
                self._dispatchTranscript(result)
                self._finishVadProcessing()
                return result

            result = PushToTalkResult(
                success=True,
                errorMessage="",
                transcribedText=transcribedText,
                assistantResponse="",
                source=source,
                audioDurationSeconds=audioDurationSeconds,
                speech=SpeechResult(
                    success=True,
                    errorMessage="",
                    transcribedText=transcribedText,
                    assistantResponse="",
                    source=source,
                    audioDurationSeconds=audioDurationSeconds,
                ),
                metadata={"vadSession": vadSession.snapshot() if vadSession is not None and hasattr(vadSession, "snapshot") else {}},
            )
            self.lastResult = result
            self._dispatchTranscript(result)
            self._emit("voice.capture.completed", result.asDict())
            if self.logger:
                self.logger.info(f"Push-to-talk capture completed with transcript={transcribedText!r}.")
            self._finishVadProcessing()
            return result
        except Exception as error:
            message = str(error)
            result = PushToTalkResult(
                success=False,
                errorMessage=message,
                source=source,
                speech=SpeechResult(success=False, errorMessage=message, source=source),
            )
            self.lastError = message
            self.lastResult = result
            self._emit("voice.capture.error", result.asDict())
            if self.logger:
                self.logger.error(f"Push-to-talk transcription failed: {error}")
            self._finishVadProcessing()
            return result

    def cancelActiveCapture(self) -> bool:
        """Cancel an active microphone capture and reset the buffer."""

        with self._lock:
            if not self._capturing and not self._frames:
                return False
            self._capturing = False
            self._captureStart = 0.0
            self._frames = []

        self._cleanupStream()
        self._cancelVadSession("push-to-talk cancelled")
        self._finishVadProcessing()
        self._emit("voice.capture.cancelled", {"source": self._activeSource})
        if self.logger:
            self.logger.info("Push-to-talk capture cancelled.")
        return True

    def isCapturing(self) -> bool:
        """Return whether a live capture is in progress."""

        return bool(self._capturing)

    def snapshot(self) -> dict[str, Any]:
        """Return capture diagnostics for UI and logging."""

        return {
            "enabled": self.enabled,
            "capturing": self.isCapturing(),
            "source": self._activeSource,
            "sampleRate": self.sampleRate,
            "device": self.microphoneDevice,
            "lastError": self.lastError,
            "lastResult": self.lastResult.asDict() if hasattr(self.lastResult, "asDict") else None,
            "vadControlled": self.vadControlled,
        }

    def _dispatchTranscript(self, result: PushToTalkResult):
        text = str(result.transcribedText or "").strip()
        if not text:
            return
        voiceManager = self.voiceManager or getattr(self.context, "voiceManager", None)
        if voiceManager is not None and hasattr(voiceManager, "handleTranscript"):
            try:
                voiceManager.handleTranscript(text, source=result.source or self._activeSource, result=result)
            except Exception as error:
                self.lastError = str(error)
                if self.logger:
                    self.logger.warning(f"Transcript dispatch failed: {error}")

    def _finishVadProcessing(self):
        if self.vadManager is not None and hasattr(self.vadManager, "markProcessingComplete"):
            try:
                self.vadManager.markProcessingComplete()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"VAD processing completion failed: {error}")

    def _cancelVadSession(self, reason: str):
        if self.vadManager is not None and hasattr(self.vadManager, "cancelSession"):
            try:
                self.vadManager.cancelSession(reason=reason)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"VAD cancel failed: {error}")

    def _openStream(self):
        if self._stream is not None:
            return
        if self._streamFactory is not None:
            self._stream = self._streamFactory(self._onAudioFrame, self.sampleRate, self.microphoneDevice)
            if hasattr(self._stream, "start"):
                self._stream.start()
            return

        sounddevice = self._ensureSounddevice()
        blockSize = max(1, int(self.sampleRate * 0.08))
        self._stream = sounddevice.InputStream(
            samplerate=self.sampleRate,
            channels=1,
            dtype="int16",
            blocksize=blockSize,
            device=self.microphoneDevice,
            callback=self._onAudioFrame,
        )
        self._stream.start()

    def _cleanupStream(self):
        stream = self._stream
        self._stream = None
        if stream is None:
            return
        try:
            if hasattr(stream, "stop"):
                stream.stop()
        finally:
            try:
                if hasattr(stream, "close"):
                    stream.close()
            except Exception:
                pass

    def _onAudioFrame(self, indata: Any, frames: int, timeInfo: Any, status: Any):
        if status and self.logger:
            self.logger.debug(f"Push-to-talk microphone status: {status}")
        try:
            np = self._ensureNumpy()
            frame = np.copy(indata).reshape(-1).astype(np.int16, copy=False)
            with self._lock:
                if self._capturing:
                    self._frames.append(frame)
            if self.vadManager is not None and getattr(self.vadManager, "enabled", False):
                try:
                    self.vadManager.processFrame(frame, sampleRate=self.sampleRate)
                except Exception as error:
                    if self.logger:
                        self.logger.warning(f"VAD frame processing failed: {error}")
        except Exception as error:
            self.lastError = str(error)
            if self.logger:
                self.logger.warning(f"Push-to-talk audio frame dropped: {error}")

    def _combineFrames(self, frames: list[Any]):
        np = self._ensureNumpy()
        if len(frames) == 1:
            return np.asarray(frames[0], dtype=np.float32) / 32768.0
        combined = np.concatenate([np.asarray(frame, dtype=np.int16).reshape(-1) for frame in frames])
        return combined.astype(np.float32) / 32768.0

    def _ensureSounddevice(self):
        if self._sounddevice is None:
            try:
                import sounddevice as sounddeviceModule
            except Exception as error:
                raise RuntimeError(f"sounddevice is unavailable: {error}") from error
            self._sounddevice = sounddeviceModule
        return self._sounddevice

    def _ensureNumpy(self):
        if self._numpy is None:
            try:
                import numpy as numpyModule
            except Exception as error:
                raise RuntimeError(f"numpy is unavailable: {error}") from error
            self._numpy = numpyModule
        return self._numpy

    def _ensureTranscriber(self):
        if self._transcriber is not None:
            return self._transcriber
        if self._transcriberFactory is not None:
            self._transcriber = self._transcriberFactory()
            return self._transcriber
        try:
            from faster_whisper import WhisperModel
        except Exception as error:
            self._transcriberError = str(error)
            raise RuntimeError(f"faster-whisper is unavailable: {error}") from error
        self._transcriber = WhisperModel(self.modelName, device=self.device, compute_type=self.computeType)
        return self._transcriber

    def _transcribe(self, audio):
        transcriber = self._ensureTranscriber()
        try:
            segments, _info = transcriber.transcribe(audio, beam_size=5, language="en", vad_filter=False)
            parts = []
            for segment in segments:
                text = str(getattr(segment, "text", "") or "").strip()
                if text:
                    parts.append(text)
            return " ".join(parts).strip()
        except Exception as error:
            self.lastError = str(error)
            raise

    def _configValue(self, key: str, default: Any = None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        return default if value in (None, "") else value

    def _configBool(self, key: str, default: bool = False) -> bool:
        value = self._configValue(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _emit(self, eventName: str, payload: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Push-to-talk event emission failed for {eventName}: {error}")
