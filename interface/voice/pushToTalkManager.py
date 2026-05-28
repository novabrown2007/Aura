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
                self._getConfigValue("voice.pushToTalkHotkey", self._getConfigValue("pushToTalkHotkey", "enter")),
            )
        )
        self.autoSpeak = self._getBoolConfig(
            "voice.pushToTalk.pushToTalkAutoSpeak",
            self._getBoolConfig("voice.pushToTalkAutoSpeak", self._getBoolConfig("pushToTalkAutoSpeak", True)),
        )
        self.tempAudioDirectory = str(
            self._getConfigValue(
                "voice.pushToTalk.pushToTalkTempAudioDirectory",
                self._getConfigValue(
                    "voice.pushToTalkTempAudioDirectory",
                    self._getConfigValue("pushToTalkTempAudioDirectory", "temp/push_to_talk"),
                ),
            )
        )
        self.active = False
        self.lastResult = PushToTalkResult()

        if self.logger:
            self.logger.info(
                "Push-to-talk manager started "
                f"(enabled={self.enabled}, hotkey={self.hotkey}, autoSpeak={self.autoSpeak}, "
                f"tempAudioDirectory={self.tempAudioDirectory})."
            )

    def startCapture(self) -> bool:
        """Start microphone capture for a push-to-talk turn."""

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
        self._emit("voice.capture.started", {"hotkey": self.hotkey})
        if self.logger:
            self.logger.info("Push-to-talk capture starting.")

        try:
            started = self.voiceManager.startVoiceCapture()
        except Exception as error:
            self._fail(f"Voice capture could not start: {error}")
            return False

        if not started:
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
            audioPath = self.voiceManager.stopVoiceCapture()
            self.active = False
            self._emit("voice.capture.finished", {"audioPath": audioPath})
            if not audioPath:
                return self._fail(getattr(self.voiceManager.recorder, "lastError", "") or "Empty recording.")

            self._emit("voice.transcription.started", {"audioPath": audioPath})
            transcription = self.voiceManager.speechToText.transcribeDetailed(audioPath)
            self.voiceManager.lastTranscription = transcription
            self._emit(
                "voice.transcription.completed",
                {
                    "success": transcription.success,
                    "text": transcription.text,
                    "errorMessage": transcription.errorMessage,
                    "audioDuration": transcription.audioDuration,
                },
            )
            if not transcription.success or not transcription.text.strip():
                return self._fail(transcription.errorMessage or "Transcription failed.", transcription=transcription, audioPath=audioPath)

            text = transcription.text.strip()
            self._emit("conversation.message.received", {"text": text, "source": "push_to_talk"})
            if self.logger:
                self.logger.info(f"Push-to-talk transcription: {text}")

            try:
                response = self.voiceManager.routeTextToAura(text)
            except Exception as error:
                return self._fail(f"Pipeline failure: {error}", transcription=transcription, audioPath=audioPath)
            response = str(response or "").strip()
            self.voiceManager.lastAssistantResponse = response
            if not response:
                return self._fail("Aura text pipeline returned an empty response.", transcription=transcription, audioPath=audioPath)

            self._emit("response.generated", {"text": response, "source": "push_to_talk"})
            speech = None
            if self.autoSpeak:
                self._emit("tts.started", {"text": response})
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
                    },
                )
                if not speech.success:
                    self._emit(
                        "voice.speech.failed",
                        {
                            "errorMessage": speech.errorMessage or "TTS failure.",
                            "source": "push_to_talk",
                        },
                    )
                    if self.logger:
                        self.logger.warning(f"Push-to-talk speech output failed after response generation: {speech.errorMessage}")

            result = PushToTalkResult(
                success=True,
                audioPath=audioPath,
                transcribedText=text,
                assistantResponse=response,
                transcription=transcription,
                speech=speech,
            )
            self.lastResult = result
            self._emit("voice.loop.completed", result.__dict__)
            if self.logger:
                self.logger.info("Push-to-talk loop completed.")
            return result
        finally:
            self.active = False
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

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Push-to-talk event emission failed for {eventName}: {error}")

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
