"""Push-to-talk voice conversation loop for Aura."""

from __future__ import annotations

from dataclasses import dataclass

from .models.speechResult import SpeechResult
from .models.transcriptionResult import TranscriptionResult


@dataclass
class PushToTalkResult:
    """Result of one push-to-talk conversation loop."""

    success: bool = False
    audioPath: str = ""
    transcribedText: str = ""
    assistantResponse: str = ""
    transcription: TranscriptionResult | None = None
    speech: SpeechResult | None = None
    errorMessage: str = ""
    source: str = "push_to_talk"


class PushToTalkManager:
    """Coordinate held push-to-talk capture through Aura's existing text pipeline."""

    def __init__(self, context=None, voiceManager=None):
        self.context = context
        self.voiceManager = voiceManager or getattr(context, "voiceManager", None)
        self.logger = context.logger.getChild("Voice.PushToTalk") if context and getattr(context, "logger", None) else None
        self.enabled = self._getBoolConfig(
            "voice.pushToTalk.enabled",
            self._getBoolConfig("voice.pushToTalkEnabled", self._getBoolConfig("voice.PTT.pushToTalkEnabled", False)),
        )
        self.hotkey = str(
            self._getConfigValue(
                "voice.pushToTalk.pushToTalkHotkey",
                self._getConfigValue(
                    "voice.PTT.pushToTalkHotkey",
                    self._getConfigValue("voice.pushToTalkHotkey", self._getConfigValue("pushToTalkHotkey", "enter")),
                ),
            )
        )
        self.autoSpeak = self._getBoolConfig(
            "voice.pushToTalk.pushToTalkAutoSpeak",
            self._getBoolConfig(
                "voice.PTT.pushToTalkAutoSpeak",
                self._getBoolConfig("voice.pushToTalkAutoSpeak", self._getBoolConfig("pushToTalkAutoSpeak", True)),
            ),
        )
        self.tempAudioDirectory = str(
            self._getConfigValue(
                "voice.pushToTalk.pushToTalkTempAudioDirectory",
                self._getConfigValue(
                    "voice.PTT.pushToTalkTempAudioDirectory",
                    self._getConfigValue(
                        "voice.pushToTalkTempAudioDirectory",
                        self._getConfigValue("pushToTalkTempAudioDirectory", "temp/push_to_talk"),
                    ),
                ),
            )
        )
        self.active = False
        self.cancelRequested = False
        self.lastResult = PushToTalkResult()
        self.captureSource = "push_to_talk"

        if self.logger:
            self.logger.info(
                "Push-to-talk manager started "
                f"(enabled={self.enabled}, hotkey={self.hotkey}, autoSpeak={self.autoSpeak}, "
                f"tempAudioDirectory={self.tempAudioDirectory})."
            )

    def startCapture(self, source: str = "push_to_talk") -> bool:
        """Start microphone capture for a push-to-talk turn."""

        self.captureSource = self._normalizeSource(source)
        self.cancelRequested = False
        if not self.enabled:
            self._fail("Push-to-talk is disabled.", emitEvent=False)
            return False
        if self.voiceManager is None:
            self._fail("Voice manager is unavailable.", emitEvent=False)
            return False
        if not getattr(self.voiceManager, "inputEnabled", False):
            self._fail("Push-to-talk requires voice.STT.enabled to be true.")
            return False
        self._applyRecorderTempDirectory()
        self._emit("voice.capture.started", {"hotkey": self.hotkey, "source": self.captureSource})
        if self.logger:
            self.logger.info(f"Voice capture starting from source={self.captureSource}.")

        try:
            self._registerCaptureOperation(self.captureSource)
            started = self.voiceManager.startVoiceCapture()
        except Exception as error:
            self._completeCaptureOperation()
            self._fail(f"Voice capture could not start: {error}")
            return False

        if not started:
            self._completeCaptureOperation()
            message = getattr(self.voiceManager.recorder, "lastError", "") or "No microphone or capture device is available."
            self._fail(message)
            return False
        self.active = True
        return True

    def stopAndProcess(self) -> PushToTalkResult:
        """Stop capture, transcribe, route the text pipeline, and speak the response."""

        if self.voiceManager is None:
            return self._fail("Voice manager is unavailable.")
        if not self.active and not self.voiceManager.recorder.isRecording():
            return self._fail("Push-to-talk capture is not active.")

        try:
            if self.cancelRequested:
                return self._fail("Voice capture cancelled.")
            source = self.captureSource
            audioPath = self.voiceManager.stopVoiceCapture()
            self.active = False
            self._emit("voice.capture.finished", {"audioPath": audioPath, "source": source})
            if not audioPath:
                return self._fail(getattr(self.voiceManager.recorder, "lastError", "") or "Empty recording.")

            self._emit("voice.transcription.started", {"audioPath": audioPath, "source": source})
            transcription = self.voiceManager.speechToText.transcribeDetailed(audioPath)
            self.voiceManager.lastTranscription = transcription
            self._emit(
                "voice.transcription.completed",
                {
                    "success": transcription.success,
                    "text": transcription.text,
                    "errorMessage": transcription.errorMessage,
                    "audioDuration": transcription.audioDuration,
                    "source": source,
                },
            )
            if not transcription.success or not transcription.text.strip():
                return self._fail(transcription.errorMessage or "Transcription failed.", transcription=transcription, audioPath=audioPath)

            text = transcription.text.strip()
            interruption = getattr(self.context, "interruptionManager", None)
            if interruption is not None and interruption.isInterruptionCommand(text):
                interruption.handleVoiceCommand(text, source=source)
                return self._cancelledResult(text, transcription, audioPath, source)

            self._emit("conversation.message.received", {"text": text, "source": source})
            if self.logger:
                self.logger.info(f"Voice transcription from {source}: {text}")

            try:
                response = self.voiceManager.routeTextToAura(text)
            except Exception as error:
                return self._fail(f"Pipeline failure: {error}", transcription=transcription, audioPath=audioPath)
            response = str(response or "").strip()
            self.voiceManager.lastAssistantResponse = response
            if not response:
                return self._fail("Aura text pipeline returned an empty response.", transcription=transcription, audioPath=audioPath)

            self._emit("response.generated", {"text": response, "source": source})
            speech = None
            if self.autoSpeak:
                speech = self._speakAssistantResponse(response, source)
                if not speech.success:
                    self._emit(
                        "voice.speech.failed",
                        {
                            "errorMessage": speech.errorMessage or "TTS failure.",
                            "source": source,
                        },
                    )
                    if self.logger:
                        self.logger.warning(f"Voice speech output failed after response generation: {speech.errorMessage}")

            result = PushToTalkResult(
                success=True,
                audioPath=audioPath,
                transcribedText=text,
                assistantResponse=response,
                transcription=transcription,
                speech=speech,
                source=source,
            )
            self.lastResult = result
            self._emit("voice.loop.completed", result.__dict__)
            if self.logger:
                self.logger.info("Push-to-talk loop completed.")
            return result
        finally:
            self.active = False
            self.cancelRequested = False
            self.captureSource = "push_to_talk"
            self._completeCaptureOperation()
            self.voiceManager._cleanupAudio()

    def runDevConsoleLoop(self, inputFn=input, outputFn=print) -> PushToTalkResult:
        """Run a simple Enter-to-start, Enter-to-stop development trigger."""

        outputFn("Press Enter to start push-to-talk recording.")
        inputFn()
        if not self.startCapture():
            outputFn(self.lastResult.errorMessage)
            return self.lastResult
        outputFn("Recording. Press Enter again to stop.")
        inputFn()
        result = self.stopAndProcess()
        if result.success:
            outputFn(f"User: {result.transcribedText}")
            outputFn(f"Aura: {result.assistantResponse}")
        else:
            outputFn(f"Push-to-talk failed: {result.errorMessage}")
        return result

    def _fail(
        self,
        message: str,
        emitEvent: bool = True,
        transcription: TranscriptionResult | None = None,
        speech: SpeechResult | None = None,
        audioPath: str = "",
        assistantResponse: str = "",
    ):
        result = PushToTalkResult(
            success=False,
            audioPath=audioPath,
            transcribedText=transcription.text if transcription else "",
            assistantResponse=assistantResponse,
            transcription=transcription,
            speech=speech,
            errorMessage=str(message or "Push-to-talk loop failed."),
            source=self.captureSource,
        )
        self.lastResult = result
        if self.logger:
            self.logger.error(result.errorMessage)
        if emitEvent:
            self._emit("voice.loop.failed", result.__dict__)
        return result

    def _applyRecorderTempDirectory(self):
        recorder = getattr(self.voiceManager, "recorder", None)
        if recorder is not None and self.tempAudioDirectory:
            recorder.tempDirectory = self.tempAudioDirectory

    def cancelActiveCapture(self) -> bool:
        """Cancel any active microphone capture."""

        self.cancelRequested = True
        cancelled = bool(self.active or (self.voiceManager and self.voiceManager.recorder.isRecording()))
        try:
            if self.voiceManager is not None and self.voiceManager.recorder.isRecording():
                self.voiceManager.stopVoiceCapture()
        except Exception:
            pass
        self.active = False
        self._completeCaptureOperation()
        return cancelled

    def _cancelledResult(self, text: str, transcription: TranscriptionResult, audioPath: str, source: str) -> PushToTalkResult:
        """Return a successful interruption result without normal routing."""

        result = PushToTalkResult(
            success=True,
            audioPath=audioPath,
            transcribedText=text,
            assistantResponse="",
            transcription=transcription,
            speech=None,
            errorMessage="",
            source=source,
        )
        self.lastResult = result
        self._emit("voice.loop.completed", result.__dict__)
        return result

    def _speakAssistantResponse(self, response: str, source: str) -> SpeechResult:
        """Speak a voice-origin assistant response through TextToSpeech."""

        self._emit("tts.started", {"text": response, "source": source})
        try:
            speech = self.voiceManager.speakResponse(response)
        except Exception as error:
            speech = SpeechResult(success=False, errorMessage=f"TTS failure: {error}")
        self._emit(
            "tts.finished",
            {
                "success": speech.success,
                "audioPath": speech.audioPath,
                "errorMessage": speech.errorMessage,
                "source": source,
            },
        )
        return speech

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Push-to-talk event emission failed for {eventName}: {error}")

    def _registerCaptureOperation(self, source: str):
        registry = getattr(self.context, "interruptionRegistry", None)
        if registry is None:
            return
        try:
            registry.registerOperation(
                "voice.capture",
                "voice",
                "capture",
                cancelHandler=lambda _context: self.cancelActiveCapture(),
                metadata={"source": source},
            )
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Failed to register voice capture interruption operation: {error}")

    def _completeCaptureOperation(self):
        registry = getattr(self.context, "interruptionRegistry", None)
        if registry is None:
            return
        try:
            registry.completeOperation("voice.capture")
        except Exception:
            pass

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if value is None or value == "":
            return default
        return value

    def _getBoolConfig(self, key: str, default=False) -> bool:
        value = self._getConfigValue(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _normalizeSource(source: str) -> str:
        normalized = str(source or "").strip().lower().replace("-", "_").replace(" ", "_")
        return normalized or "push_to_talk"
