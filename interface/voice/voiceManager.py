"""Coordinate local voice input and output for Aura."""

from __future__ import annotations

import time

from .models.speechResult import SpeechResult
from .models.transcriptionResult import TranscriptionResult
from .speechQueue import SpeechQueue
from .speechToText import SpeechToText
from .textToSpeech import TextToSpeech
from .voiceRecorder import VoiceRecorder
from .pushToTalkManager import PushToTalkManager


class VoiceManager:
    """Manage local voice capture and local speech playback."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Voice") if context and getattr(context, "logger", None) else None

        self.inputEnabled = self._getBoolConfig("voice.STT.enabled", self._getBoolConfig("voice.enabled", False))
        self.inputModelName = self._getConfigValue("voice.model", "small.en")
        self.inputDevice = self._getConfigValue("voice.device", "cpu")
        self.inputComputeType = self._getConfigValue("voice.computeType", "int8")
        self.inputSampleRate = int(self._getConfigValue("voice.sampleRate", 16000))

        self.outputEnabled = self._getBoolConfig("voice.voiceEnabled", self._getBoolConfig("voiceEnabled", True))
        self.outputModelPath = self._getConfigValue("voice.voiceModelPath", self._getConfigValue("voiceModelPath", "en_US-lessac-medium"))
        self.outputDirectory = self._getConfigValue("voice.voiceOutputDirectory", self._getConfigValue("voiceOutputDirectory", "temp/voice"))
        self.playbackEnabled = self._getBoolConfig("voice.voicePlaybackEnabled", self._getBoolConfig("voicePlaybackEnabled", True))
        self.outputSampleRate = int(self._getConfigValue("voice.voiceSampleRate", self._getConfigValue("voiceSampleRate", 22050)))
        self.pushToTalkEnabled = self._getBoolConfig(
            "voice.pushToTalk.enabled",
            self._getBoolConfig("voice.pushToTalkEnabled", self._getBoolConfig("voice.PTT.pushToTalkEnabled", False)),
        )
        self.pushToTalkTempAudioDirectory = self._getConfigValue(
            "pushToTalkTempAudioDirectory",
            self._getConfigValue("voice.pushToTalkTempAudioDirectory", "temp/push_to_talk"),
        )

        self.speechToText = SpeechToText(
            context,
            modelName=str(self.inputModelName),
            device=str(self.inputDevice),
            computeType=str(self.inputComputeType),
        )
        self.recorder = VoiceRecorder(
            context,
            sampleRate=self.inputSampleRate,
            tempDirectory=str(self.pushToTalkTempAudioDirectory),
        )
        self.textToSpeech = TextToSpeech(
            context,
            modelPath=str(self.outputModelPath),
            outputDirectory=str(self.outputDirectory),
            playbackEnabled=bool(self.playbackEnabled and self.outputEnabled),
            sampleRate=self.outputSampleRate,
        )
        self.audioPlayer = self.textToSpeech.audioPlayer
        self.speechQueue = SpeechQueue(context, self.textToSpeech)
        self.pushToTalkManager = PushToTalkManager(context, self)

        self.lastTranscription = TranscriptionResult()
        self.lastSpeech = SpeechResult()
        self.lastAssistantResponse = ""
        self.lastAudioPath = ""
        self.voiceActive = False

        if self.context is not None:
            self.context.voiceManager = self
            self.context.textToSpeech = self.textToSpeech
            self.context.audioPlayer = self.audioPlayer
            self.context.speechQueue = self.speechQueue
            self.context.pushToTalkManager = self.pushToTalkManager

        self._log(
            "Voice manager started "
            f"(stt_enabled={self.inputEnabled}, tts_enabled={self.outputEnabled}, "
            f"push_to_talk_enabled={self.pushToTalkEnabled})."
        )

    def startVoiceCapture(self):
        """Start recording a local push-to-talk voice capture."""

        if not self.inputEnabled:
            self._log("Voice input is disabled in configuration.")
            return False
        started = self.recorder.startRecording()
        self.voiceActive = bool(started)
        return started

    def stopVoiceCapture(self):
        """Stop recording and persist the audio to a temporary WAV file."""

        if not self.voiceActive and not self.recorder.isRecording():
            return ""

        stopped = self.recorder.stopRecording()
        if not stopped:
            self.voiceActive = False
            return ""

        self.voiceActive = False
        path = self.recorder.saveRecording()
        self.lastAudioPath = path or ""
        return self.lastAudioPath

    def processVoiceInput(self, recordSeconds: float = 5.0) -> TranscriptionResult:
        """Record, transcribe, route text into Aura, and clean up temp audio."""

        if not self.inputEnabled:
            result = TranscriptionResult(success=False, errorMessage="Voice input is disabled.")
            self.lastTranscription = result
            return result

        if not self.startVoiceCapture():
            result = TranscriptionResult(success=False, errorMessage=self.recorder.lastError or "Voice capture could not start.")
            self.lastTranscription = result
            return result

        try:
            if recordSeconds and recordSeconds > 0:
                time.sleep(float(recordSeconds))
            audioPath = self.stopVoiceCapture()
            if not audioPath:
                result = TranscriptionResult(success=False, errorMessage=self.recorder.lastError or "No audio was recorded.")
                self.lastTranscription = result
                return result

            result = self.speechToText.transcribeDetailed(audioPath)
            self.lastTranscription = result
            if result.success and result.text.strip():
                self.lastAssistantResponse = self._sendTextToAura(result.text)
            else:
                self.lastAssistantResponse = ""
            return result
        finally:
            self._cleanupAudio()

    def startPushToTalk(self):
        """Start a held push-to-talk capture."""

        return self.pushToTalkManager.startCapture()

    def stopPushToTalk(self):
        """Stop and process the active push-to-talk capture."""

        return self.pushToTalkManager.stopAndProcess()

    def speakResponse(self, text: str):
        """Queue and play assistant speech through the local TTS stack."""

        if not self.outputEnabled:
            return SpeechResult(success=False, errorMessage="Voice playback is disabled.")
        if self.speechQueue is None:
            return SpeechResult(success=False, errorMessage="Voice speech queue is unavailable.")

        results = self.speechQueue.enqueue(text)
        if results:
            self.lastSpeech = results[-1]
            return self.lastSpeech

        result = SpeechResult(success=False, errorMessage="No speech was queued.")
        self.lastSpeech = result
        return result

    def speak(self, text: str):
        """Speak text using the current assistant voice configuration."""

        return self.speakResponse(text)

    def shutdown(self):
        """Release cached voice resources."""

        try:
            self.recorder.cleanup()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice recorder shutdown failed: {error}")
        try:
            self.speechQueue.clearQueue()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Speech queue shutdown failed: {error}")
        try:
            self.textToSpeech.shutdown()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Text-to-speech shutdown failed: {error}")
        self.voiceActive = False
        self.lastAudioPath = ""

    def _sendTextToAura(self, text: str) -> str:
        """Route a transcribed voice command through Aura's existing text pipeline."""

        text = str(text or "").strip()
        if not text:
            return ""

        try:
            interpreter = getattr(self.context, "interpreter", None)
            router = getattr(self.context, "intentRouter", None)
            if interpreter is not None and router is not None:
                intent = interpreter.interpret(text)
                response = router.route(intent)
                return str(response)

            llm = getattr(self.context, "llm", None)
            if llm is not None and hasattr(llm, "generateResponse"):
                return str(llm.generateResponse(text))
        except Exception as error:
            if self.logger:
                self.logger.error(f"Voice text routing failed: {error}")
            return f"Error: {error}"

        return ""

    def routeTextToAura(self, text: str) -> str:
        """Public wrapper for routing transcribed text through Aura's text pipeline."""

        return self._sendTextToAura(text)

    def _cleanupAudio(self):
        """Remove the temporary voice recording after processing."""

        try:
            self.recorder.cleanup()
            if self.logger and self.lastAudioPath:
                self.logger.info(f"Cleaned up temporary voice file: {self.lastAudioPath}")
        finally:
            self.lastAudioPath = ""

    def _getConfigValue(self, key: str, default=None):
        """Read a voice-related config value from Aura's config interface."""

        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, default)
        if value is None or value == "":
            return default
        return value

    def _getBoolConfig(self, key: str, default=False) -> bool:
        """Read a voice-related boolean config value."""

        value = self._getConfigValue(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _log(self, message: str):
        """Log or ignore a voice message when the logger is missing."""

        if self.logger:
            self.logger.info(message)
