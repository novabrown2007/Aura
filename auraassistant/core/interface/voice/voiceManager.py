"""Coordinate local push-to-talk voice capture and transcription."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .models.transcriptionResult import TranscriptionResult
from .speechToText import SpeechToText
from .voiceRecorder import VoiceRecorder


class VoiceManager:
    """Manage local voice capture without owning assistant reasoning."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Voice") if context and getattr(context, "logger", None) else None
        self.enabled = self._getBoolConfig("voice.enabled", self._getBoolConfig("voiceEnabled", False))
        self.modelName = self._getConfigValue("voice.model", self._getConfigValue("voiceModel", "small.en"))
        self.device = self._getConfigValue("voice.device", self._getConfigValue("voiceDevice", "cpu"))
        self.computeType = self._getConfigValue("voice.computeType", self._getConfigValue("voiceComputeType", "int8"))
        self.sampleRate = int(self._getConfigValue("voice.sampleRate", self._getConfigValue("voiceSampleRate", 16000)))
        self.speechToText = SpeechToText(
            context,
            modelName=str(self.modelName),
            device=str(self.device),
            computeType=str(self.computeType),
        )
        self.recorder = VoiceRecorder(context, sampleRate=self.sampleRate)
        self.lastTranscription = TranscriptionResult()
        self.lastAssistantResponse = ""
        self.lastAudioPath = ""
        self.voiceActive = False

    def startVoiceCapture(self):
        """Start recording a local push-to-talk voice capture."""

        if not self.enabled:
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

        if not self.enabled:
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

    def shutdown(self):
        """Release cached voice resources."""

        try:
            self.recorder.cleanup()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice recorder shutdown failed: {error}")
        try:
            self.speechToText.shutdown()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Speech-to-text shutdown failed: {error}")
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
