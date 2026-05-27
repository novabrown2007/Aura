"""Tests for Aura's local voice input and output layers."""

from __future__ import annotations

import sys
import os
import tempfile
import types
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from interface.voice import AudioPlayer, PushToTalkManager, SpeechQueue, SpeechToText, TextToSpeech, VoiceManager, VoiceRecorder
from interface.voice.models import SpeechResult, TranscriptionResult
from testing.tests.support.fakes import make_context


class FakeWhisperModel:
    """Deterministic Whisper stub for cache and transcription testing.tests."""

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


class FakePiperVoice:
    """Deterministic Piper stub for local synthesis testing.tests."""

    init_count = 0

    def __init__(self):
        FakePiperVoice.init_count += 1

    @classmethod
    def load(cls, model_path):
        instance = cls()
        instance.model_path = str(model_path)
        return instance

    def synthesize_wav(self, text, audio_file):
        with wave.open(audio_file, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(22050)
            handle.writeframes(np.ones((2205,), dtype=np.int16).tobytes())


class FakeSoundDeviceModule:
    """Sounddevice replacement for playback testing.tests."""

    played = []
    stopped = False

    @classmethod
    def play(cls, audio, sample_rate):
        cls.played.append((audio, sample_rate))

    @classmethod
    def wait(cls):
        return None

    @classmethod
    def stop(cls):
        cls.stopped = True


class FakeInputStream:
    """Minimal sounddevice InputStream replacement for recorder testing.tests."""

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


class RecordingEventManager:
    """Collect emitted events for push-to-talk testing.tests."""

    def __init__(self):
        self.events = []

    def emit(self, eventName, data=None):
        self.events.append((eventName, data or {}))


class FakePushRecorder:
    """Recorder fake for the push-to-talk loop."""

    def __init__(self, audioPath="fake.wav", startOk=True):
        self.audioPath = audioPath
        self.startOk = startOk
        self.recording = False
        self.lastError = ""
        self.tempDirectory = ""

    def startRecording(self):
        if not self.startOk:
            self.lastError = "No microphone available."
            return False
        self.recording = True
        return True

    def stopRecording(self):
        wasRecording = self.recording
        self.recording = False
        return wasRecording

    def saveRecording(self):
        return self.audioPath

    def isRecording(self):
        return self.recording

    def cleanup(self):
        self.recording = False


class FakePushSpeechToText:
    """STT fake for push-to-talk testing.tests."""

    def __init__(self, result):
        self.result = result

    def transcribeDetailed(self, audioPath):
        return self.result


class VoiceTests(unittest.TestCase):
    """Validate local speech-to-text and speech-synthesis behavior."""

    def setUp(self):
        self.context = make_context()
        self.context.config._data["voice"] = {
            "enabled": True,
            "model": "small.en",
            "device": "cpu",
            "computeType": "int8",
            "sampleRate": 16000,
            "voiceEnabled": True,
            "voiceModelPath": "en_US-lessac-medium.onnx",
            "voiceOutputDirectory": "temp/voice",
            "voicePlaybackEnabled": True,
            "voiceSampleRate": 22050,
            "pushToTalkEnabled": True,
            "pushToTalkHotkey": "enter",
            "pushToTalkAutoSpeak": True,
            "pushToTalkTempAudioDirectory": "temp/push_to_talk",
        }
        self.context.config._data["pushToTalkEnabled"] = True
        self.context.config._data["pushToTalkHotkey"] = "enter"
        self.context.config._data["pushToTalkAutoSpeak"] = True
        self.context.config._data["pushToTalkTempAudioDirectory"] = "temp/push_to_talk"
        self.context.eventManager = RecordingEventManager()

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

    def test_speech_to_text_applies_configured_hugging_face_token(self):
        original_module = sys.modules.get("faster_whisper")
        old_token = os.environ.get("HF_TOKEN")
        os.environ.pop("HF_TOKEN", None)
        fake_module = types.SimpleNamespace(WhisperModel=FakeWhisperModel)
        sys.modules["faster_whisper"] = fake_module

        try:
            self.context.config._data["huggingFace"] = {"apiToken": "hf_config_token"}
            stt = SpeechToText(self.context)
            stt.initialize()

            self.assertEqual(os.environ.get("HF_TOKEN"), "hf_config_token")
        finally:
            if original_module is None:
                sys.modules.pop("faster_whisper", None)
            else:
                sys.modules["faster_whisper"] = original_module
            if old_token is None:
                os.environ.pop("HF_TOKEN", None)
            else:
                os.environ["HF_TOKEN"] = old_token

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

    def test_text_to_speech_initializes_once_and_generates_audio(self):
        original_piper = sys.modules.get("piper.voice")
        original_sounddevice = sys.modules.get("sounddevice")

        sys.modules["piper.voice"] = types.SimpleNamespace(PiperVoice=FakePiperVoice)
        sys.modules["sounddevice"] = FakeSoundDeviceModule

        voice_dir = tempfile.TemporaryDirectory()
        try:
            FakeSoundDeviceModule.played = []
            FakePiperVoice.init_count = 0
            model_path = Path(voice_dir.name) / "en_US-lessac-medium.onnx"
            model_path.write_bytes(b"fake-onnx")

            tts = TextToSpeech(
                self.context,
                modelPath=str(model_path),
                outputDirectory=voice_dir.name,
                playbackEnabled=True,
                sampleRate=22050,
            )

            first = tts.initialize()
            second = tts.initialize()
            self.assertIs(first, second)
            self.assertEqual(FakePiperVoice.init_count, 1)

            result = tts.speak("Hello Aura. Voice systems are online.")
            self.assertTrue(result.success)
            self.assertTrue(result.audioPath)
            self.assertGreaterEqual(result.generationTime, 0.0)
            self.assertGreaterEqual(result.playbackDuration, 0.0)
            self.assertFalse(Path(result.audioPath).exists())
            self.assertEqual(FakeSoundDeviceModule.played[0][1], 22050)
        finally:
            if original_piper is None:
                sys.modules.pop("piper.voice", None)
            else:
                sys.modules["piper.voice"] = original_piper
            if original_sounddevice is None:
                sys.modules.pop("sounddevice", None)
            else:
                sys.modules["sounddevice"] = original_sounddevice
            voice_dir.cleanup()

    def test_text_to_speech_reports_searched_model_paths(self):
        original_piper = sys.modules.get("piper.voice")
        sys.modules["piper.voice"] = types.SimpleNamespace(PiperVoice=FakePiperVoice)

        try:
            tts = TextToSpeech(self.context, modelPath="missing-voice", outputDirectory="temp/voice")
            result = tts.generateSpeech("Hello Aura.")

            self.assertFalse(result.success)
            self.assertIn("Voice model not found: missing-voice", result.errorMessage)
            self.assertIn("missing-voice.onnx", result.errorMessage)
            self.assertIn("voice.TTS.voiceModelPath", result.errorMessage)
        finally:
            if original_piper is None:
                sys.modules.pop("piper.voice", None)
            else:
                sys.modules["piper.voice"] = original_piper

    def test_audio_player_plays_wave_files(self):
        original_sounddevice = sys.modules.get("sounddevice")
        sys.modules["sounddevice"] = FakeSoundDeviceModule
        try:
            FakeSoundDeviceModule.played = []
            player = AudioPlayer(self.context)
            audio_path = self._create_wav_file(sample_rate=22050)
            try:
                duration = player.playAudio(str(audio_path))
                self.assertGreaterEqual(duration, 0.0)
                self.assertFalse(player.isPlaying())
                self.assertEqual(FakeSoundDeviceModule.played[0][1], 22050)
            finally:
                audio_path.unlink(missing_ok=True)
        finally:
            if original_sounddevice is None:
                sys.modules.pop("sounddevice", None)
            else:
                sys.modules["sounddevice"] = original_sounddevice

    def test_speech_queue_serializes_speech(self):
        spoken = []

        class FakeTTS:
            def speak(self, text):
                spoken.append(text)
                return SpeechResult(success=True, audioPath=f"{text}.wav")

        queue = SpeechQueue(self.context, FakeTTS())
        results = queue.enqueue("first line")
        results.extend(queue.enqueue("second line"))

        self.assertEqual(spoken, ["first line", "second line"])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result.success for result in results))

    def test_voice_manager_routes_transcription_through_existing_pipeline(self):
        self.context.interpreter = SimpleNamespace(
            interpret=lambda text: SimpleNamespace(name="llm", raw=text)
        )
        self.context.intentRouter = SimpleNamespace(
            route=lambda intent: f"routed:{intent.raw}"
        )

        manager = VoiceManager(self.context)
        manager.inputEnabled = True
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

    def test_push_to_talk_routes_transcription_through_text_pipeline_and_tts(self):
        manager = VoiceManager(self.context)
        manager.recorder = FakePushRecorder()
        manager.speechToText = FakePushSpeechToText(
            TranscriptionResult(text="hello aura", success=True, language="en")
        )
        routed = []
        spoken = []
        manager.routeTextToAura = lambda text: (routed.append(text), "Hello Nova.")[1]
        manager.speakResponse = lambda text: (spoken.append(text), SpeechResult(success=True, audioPath="tts.wav"))[1]

        self.assertTrue(manager.startPushToTalk())
        result = manager.stopPushToTalk()

        self.assertTrue(result.success)
        self.assertEqual(routed, ["hello aura"])
        self.assertEqual(spoken, ["Hello Nova."])
        emitted = [name for name, _ in self.context.eventManager.events]
        self.assertIn("voice.capture.started", emitted)
        self.assertIn("voice.capture.finished", emitted)
        self.assertIn("voice.transcription.started", emitted)
        self.assertIn("voice.transcription.completed", emitted)
        self.assertIn("conversation.message.received", emitted)
        self.assertIn("response.generated", emitted)
        self.assertIn("tts.started", emitted)
        self.assertIn("tts.finished", emitted)
        self.assertIn("voice.loop.completed", emitted)

    def test_push_to_talk_handles_missing_microphone(self):
        manager = VoiceManager(self.context)
        manager.recorder = FakePushRecorder(startOk=False)

        self.assertFalse(manager.startPushToTalk())

        self.assertIn("No microphone", manager.pushToTalkManager.lastResult.errorMessage)
        emitted = [name for name, _ in self.context.eventManager.events]
        self.assertIn("voice.capture.started", emitted)
        self.assertIn("voice.loop.failed", emitted)

    def test_push_to_talk_requires_stt_input_enabled(self):
        manager = VoiceManager(self.context)
        manager.inputEnabled = False

        self.assertFalse(manager.startPushToTalk())

        self.assertIn("voice.STT.enabled", manager.pushToTalkManager.lastResult.errorMessage)

    def test_push_to_talk_handles_transcription_failure(self):
        manager = VoiceManager(self.context)
        manager.recorder = FakePushRecorder()
        manager.speechToText = FakePushSpeechToText(
            TranscriptionResult(success=False, errorMessage="Empty transcription.")
        )

        self.assertTrue(manager.startPushToTalk())
        result = manager.stopPushToTalk()

        self.assertFalse(result.success)
        self.assertEqual(result.errorMessage, "Empty transcription.")
        emitted = [name for name, _ in self.context.eventManager.events]
        self.assertIn("voice.transcription.completed", emitted)
        self.assertIn("voice.loop.failed", emitted)

    def test_push_to_talk_handles_tts_failure(self):
        manager = VoiceManager(self.context)
        manager.recorder = FakePushRecorder()
        manager.speechToText = FakePushSpeechToText(
            TranscriptionResult(text="hello aura", success=True, language="en")
        )
        manager.routeTextToAura = lambda text: "Hello Nova."
        manager.speakResponse = lambda text: SpeechResult(success=False, errorMessage="Piper failed.")

        self.assertTrue(manager.startPushToTalk())
        result = manager.stopPushToTalk()

        self.assertTrue(result.success)
        self.assertEqual(result.transcribedText, "hello aura")
        self.assertEqual(result.assistantResponse, "Hello Nova.")
        self.assertEqual(result.speech.errorMessage, "Piper failed.")
        emitted = [name for name, _ in self.context.eventManager.events]
        self.assertIn("tts.finished", emitted)
        self.assertIn("voice.speech.failed", emitted)
        self.assertIn("voice.loop.completed", emitted)
        self.assertNotIn("voice.loop.failed", emitted)


if __name__ == "__main__":
    unittest.main()
