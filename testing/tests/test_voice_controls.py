"""Tests for Aura's voice input and orchestration flow."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

import numpy as np

from core.voice.pushToTalkManager import PushToTalkManager
from core.voice.voiceManager import VoiceManager
from testing.tests.support.fakes import DictConfig, make_context


class FakeStream:
    """Capture audio callback invocations without real hardware."""

    def __init__(self, callback):
        self.callback = callback
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True
        return self

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True

    def emit(self, samples):
        self.callback(np.asarray(samples, dtype=np.int16), len(samples), None, None)


class FakeTranscriber:
    """Return a deterministic transcript for a captured audio buffer."""

    def transcribe(self, audio, beam_size=5, language="en", vad_filter=False):
        return [SimpleNamespace(text="hello aura")], SimpleNamespace(language=language)


class VoiceControlsTests(unittest.TestCase):
    """Exercise the voice runtime without touching a physical microphone."""

    def setUp(self):
        self.context = make_context(
            extra={
                "config": DictConfig(
                    {
                        "voice": {
                            "pushToTalk": {
                                "enabled": True,
                                "pushToTalkAutoSpeak": True,
                            },
                            "STT": {
                                "model": "small.en",
                                "device": "cpu",
                                "computeType": "int8",
                                "sampleRate": 16000,
                            },
                            "vad": {
                                "vadEnabled": False,
                            },
                        },
                    }
                ),
            }
        )
        self.context.eventManager = SimpleNamespace(
            emit=lambda *_args, **_kwargs: None,
            subscribe=lambda *_args, **_kwargs: None,
            unsubscribe=lambda *_args, **_kwargs: None,
        )

    def test_push_to_talk_transcribes_and_dispatches_transcript(self):
        transcripts = []
        ptt = PushToTalkManager(
            self.context,
            vadManager=SimpleNamespace(
                enabled=False,
                startSession=lambda *args, **kwargs: None,
                finalizeSession=lambda *args, **kwargs: None,
                markProcessingComplete=lambda: None,
                cancelSession=lambda *args, **kwargs: False,
                processFrame=lambda *args, **kwargs: None,
            ),
            voiceManager=SimpleNamespace(handleTranscript=lambda text, source="push_to_talk", result=None: transcripts.append((text, source))),
            streamFactory=lambda callback, sample_rate, device: FakeStream(callback),
            transcriberFactory=lambda: FakeTranscriber(),
        )

        self.assertTrue(ptt.startCapture(source="button"))
        ptt._stream.emit([[1000], [2000], [3000]])
        result = ptt.stopAndProcess()

        self.assertTrue(result.success)
        self.assertEqual(result.transcribedText, "hello aura")
        self.assertEqual(transcripts, [("hello aura", "button")])

    def test_voice_manager_queues_transcript_handler_on_ui_thread(self):
        calls = []
        voiceManager = VoiceManager(
            self.context,
            vadManager=SimpleNamespace(
                enabled=False,
                startSession=lambda *args, **kwargs: None,
                finalizeSession=lambda *args, **kwargs: None,
                markProcessingComplete=lambda: None,
                cancelSession=lambda *args, **kwargs: False,
            ),
            pushToTalkManager=SimpleNamespace(
                voiceManager=None,
                snapshot=lambda: {},
                isCapturing=lambda: False,
                startCapture=lambda *args, **kwargs: True,
                stopAndProcess=lambda: None,
                cancelActiveCapture=lambda: False,
            ),
            wakeWordManager=SimpleNamespace(initialize=lambda: True, shutdown=lambda: None, snapshot=lambda: {}),
            post_ui_event=lambda callback: callback(),
        )

        voiceManager.setTranscriptHandler(lambda text, source, result=None: calls.append((text, source)))
        handled = voiceManager.handleTranscript("hello aura", source="push_to_talk")

        self.assertTrue(handled)
        self.assertEqual(calls, [("hello aura", "push_to_talk")])


if __name__ == "__main__":
    unittest.main()
