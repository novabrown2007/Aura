"""Tests for Aura's local push-to-talk voice layer."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from auraassistant.core.interface.voice import SpeechToText, VoiceManager, VoiceRecorder
from auraassistant.core.interface.voice.models import TranscriptionResult
from tests.support.fakes import make_context


class FakeWhisperModel:
    """Deterministic Whisper stub for cache and transcription tests."""

    init_count = 0

    def __init__(self, model_name, device="cpu", compute_type="int8"):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        FakeWhisperModel.init_count += 1

    def transcribe(self, audio_path, language="en", beam_size=1, vad_filter=False):
        segments = [SimpleNamespace(text="hello"), SimpleNamespace(text="aura")]
        info = SimpleNamespace(language=language)
        return iter(segments), info


class FakeInputStream:
    """Minimal sounddevice InputStream replacement for recorder tests."""

    def __init__(self, samplerate, channels, dtype, callback):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.callback = callback
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True
        chunk = np.array([[1], [2], [3]], dtype=np.int16)
        self.callback(chunk, chunk.shape[0], None, None)

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


class VoiceTests(unittest.TestCase):
    """Validate local speech-to-text behavior and Aura pipeline integration."""

    def setUp(self):
        self.context = make_context()
        self.context.config._data["voice"] = {
            "enabled": True,
            "model": "small.en",
            "device": "cpu",
            "computeType": "int8",
            "sampleRate": 16000,
        }

    def _create_wav_file(self, frames=1600, sample_rate=16000):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp.close()
        path = Path(temp.name)
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(np.zeros((frames,), dtype=np.int16).tobytes())
        return path

    def test_speech_to_text_initializes_once_and_transcribes(self):
        original_module = sys.modules.get("faster_whisper")
        fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
        sys.modules["faster_whisper"] = fake_module

        try:
            FakeWhisperModel.init_count = 0
            stt = SpeechToText(self.context)
            first = stt.initialize()
            second = stt.initialize()

            self.assertIs(first, second)
            self.assertEqual(FakeWhisperModel.init_count, 1)

            audio_path = self._create_wav_file()
            try:
                result = stt.transcribeDetailed(str(audio_path))
                self.assertTrue(result.success)
                self.assertEqual(result.text, "hello aura")
                self.assertEqual(result.language, "en")
                self.assertGreaterEqual(result.transcriptionTime, 0.0)
            finally:
                audio_path.unlink(missing_ok=True)
        finally:
            if original_module is None:
                sys.modules.pop("faster_whisper", None)
            else:
                sys.modules["faster_whisper"] = original_module

    def test_voice_recorder_saves_mono_wav(self):
        recorder = VoiceRecorder(self.context, sampleRate=16000)
        recorder._sounddevice = SimpleNamespace(InputStream=FakeInputStream)
        recorder._numpy = np

        self.assertTrue(recorder.startRecording())
        self.assertTrue(recorder.stopRecording())

        path = recorder.saveRecording()
        try:
            self.assertIsNotNone(path)
            with wave.open(path, "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getframerate(), 16000)
                self.assertGreater(handle.getnframes(), 0)
        finally:
            if path:
                Path(path).unlink(missing_ok=True)

    def test_voice_manager_routes_transcription_through_existing_pipeline(self):
        self.context.interpreter = SimpleNamespace(
            interpret=lambda text: SimpleNamespace(name="llm", raw=text)
        )
        self.context.intentRouter = SimpleNamespace(
            route=lambda intent: f"routed:{intent.raw}"
        )

        manager = VoiceManager(self.context)
        manager.enabled = True
        manager.startVoiceCapture = lambda: True
        manager.stopVoiceCapture = lambda: "fake.wav"
        manager.speechToText.transcribeDetailed = lambda path: TranscriptionResult(
            text="turn on the lights",
            success=True,
            language="en",
            transcriptionTime=0.01,
            audioDuration=0.25,
        )
        manager._cleanupAudio = lambda: None

        result = manager.processVoiceInput(recordSeconds=0)

        self.assertTrue(result.success)
        self.assertEqual(result.text, "turn on the lights")
        self.assertEqual(manager.lastAssistantResponse, "routed:turn on the lights")

    def test_voice_manager_returns_clean_failure_when_disabled(self):
        self.context.config._data["voice"]["enabled"] = False
        manager = VoiceManager(self.context)

        result = manager.processVoiceInput(recordSeconds=0)

        self.assertFalse(result.success)
        self.assertEqual(result.errorMessage, "Voice input is disabled.")


if __name__ == "__main__":
    unittest.main()
