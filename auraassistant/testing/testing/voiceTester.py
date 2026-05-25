"""Voice testing helpers for assistant ecosystem simulations."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any


@dataclass(slots=True)
class VoiceTestResult:
    """Outcome of a simulated voice interaction."""

    text: str
    transcription: str
    response: str
    transcriptionTime: float = 0.0
    responseTime: float = 0.0


class VoiceTester:
    """Simulate push-to-talk and transcription timing for assistant testing."""

    def __init__(self, context=None, voiceManager=None, tracer=None):
        self.context = context
        self.voiceManager = voiceManager or getattr(context, "voiceManager", None)
        self.tracer = tracer
        self.logger = context.logger.getChild("Testing.Voice") if context and getattr(context, "logger", None) else None

    def simulatePushToTalk(self, text: str, recordSeconds: float = 0.0, voiceInput: dict[str, Any] | None = None):
        """Simulate a push-to-talk interaction without requiring real audio."""

        start = perf_counter()
        transcript = str((voiceInput or {}).get("text") or text or "").strip()
        if not transcript:
            result = VoiceTestResult(text=str(text or ""), transcription="", response="", transcriptionTime=0.0, responseTime=0.0)
            if self.tracer:
                self.tracer.trace("voice", "push-to-talk", {"text": text, "transcript": "", "response": ""})
            return result

        responseStart = perf_counter()
        response = self._routeTranscription(transcript)
        responseTime = perf_counter() - responseStart
        transcriptionTime = perf_counter() - start

        if self.voiceManager is not None and hasattr(self.voiceManager, "speakResponse") and response:
            try:
                self.voiceManager.speakResponse(response)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Voice playback simulation failed: {error}")

        if self.tracer:
            self.tracer.trace("voice", "push-to-talk", {"text": text, "transcript": transcript, "response": response})

        return VoiceTestResult(
            text=str(text or ""),
            transcription=transcript,
            response=str(response or ""),
            transcriptionTime=transcriptionTime,
            responseTime=responseTime,
        )

    def measureResponseTime(self, text: str):
        """Return a simple timing placeholder for voice response testing."""

        result = self.simulatePushToTalk(text)
        return {"transcription": result.transcription, "response": result.response}

    def _routeTranscription(self, transcript: str) -> str:
        """Route a simulated transcript through the existing text pipeline."""

        interpreter = getattr(self.context, "interpreter", None)
        router = getattr(self.context, "intentRouter", None)
        if interpreter is not None and router is not None:
            try:
                intent = interpreter.interpret(transcript)
                return str(router.route(intent))
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Intent routing failed in voice tester: {error}")

        llm = getattr(self.context, "llm", None)
        if llm is not None and hasattr(llm, "generateResponse"):
            try:
                return str(llm.generateResponse(transcript))
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"LLM routing failed in voice tester: {error}")

        return transcript
