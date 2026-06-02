"""High-level voice orchestration for Aura."""

from __future__ import annotations

from threading import Thread
from typing import Any, Callable

from .pushToTalkManager import PushToTalkManager
from .vad import VADManager
from .wakeWord import WakeWordManager


class SimpleSpeechQueue:
    """Minimal speech queue placeholder used by interruption and observability layers."""

    def __init__(self):
        self._processing = False
        self._queue: list[str] = []
        self.lastItem = ""

    def enqueue(self, text: str):
        text = str(text or "").strip()
        if not text:
            return False
        self.lastItem = text
        self._queue.append(text)
        self._processing = True
        return True

    def finish(self):
        self._processing = False
        if self._queue:
            self._queue.pop(0)

    def cancel(self):
        self._queue.clear()
        self._processing = False

    def clearQueue(self):
        self.cancel()


class VoiceManager:
    """Coordinate push-to-talk, wake word, and spoken response delivery."""

    def __init__(
        self,
        context=None,
        vadManager: VADManager | None = None,
        pushToTalkManager: PushToTalkManager | None = None,
        wakeWordManager: WakeWordManager | None = None,
        post_ui_event: Callable[[Callable[[], None]], None] | None = None,
    ):
        self.context = context
        self.logger = context.logger.getChild("Voice") if context and getattr(context, "logger", None) else None
        self.post_ui_event = post_ui_event
        self.transcriptHandler: Callable[[str, str, Any], Any] | None = None
        self.lastTranscript = ""
        self.lastTranscriptSource = ""
        self.lastSpokenText = ""
        self.speechQueue = SimpleSpeechQueue()
        self.textToSpeech = getattr(context, "textToSpeech", None)
        self.audioPlayer = getattr(context, "audioPlayer", None)

        self.vadManager = vadManager or getattr(context, "vadManager", None) or VADManager(context)
        self.pushToTalkManager = pushToTalkManager or PushToTalkManager(context, vadManager=self.vadManager, voiceManager=self)
        self.wakeWordManager = wakeWordManager or WakeWordManager(context)

        self._eventSubscribed = False
        self._fallbackThread: Thread | None = None

        if self.context is not None:
            self.context.voiceManager = self
            self.context.pushToTalkManager = self.pushToTalkManager
            self.context.wakeWordManager = self.wakeWordManager
            self.context.vadManager = self.vadManager
            self.context.textToSpeech = self.textToSpeech
            self.context.audioPlayer = self.audioPlayer
            self.context.speechQueue = self.speechQueue

        self.pushToTalkManager.voiceManager = self
        self.initialize()

    def initialize(self):
        """Bind event listeners and start the wake-word listener if enabled."""

        if self._eventSubscribed:
            return self

        self._subscribeToVoiceEvents()
        if self.wakeWordManager is not None:
            try:
                self.wakeWordManager.initialize()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Wake word initialization failed: {error}")
        self._eventSubscribed = True
        return self

    def shutdown(self):
        """Stop all voice subsystems and release local resources."""

        try:
            if self.wakeWordManager is not None and hasattr(self.wakeWordManager, "shutdown"):
                self.wakeWordManager.shutdown()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Wake word shutdown failed: {error}")

        try:
            if self.pushToTalkManager is not None and hasattr(self.pushToTalkManager, "cancelActiveCapture"):
                self.pushToTalkManager.cancelActiveCapture()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Push-to-talk shutdown failed: {error}")

        try:
            self.speechQueue.cancel()
        except Exception:
            pass

        thread = self._fallbackThread
        if thread is not None and thread.is_alive():
            try:
                thread.join(timeout=1.0)
            except Exception:
                pass

        self._unsubscribeFromVoiceEvents()

    def setPostUIEvent(self, callback: Callable[[Callable[[], None]], None] | None):
        """Set the callback used to marshal UI work onto the Tk thread."""

        self.post_ui_event = callback

    def setTranscriptHandler(self, handler: Callable[[str, str, Any], Any] | None):
        """Set the callback that receives transcripts before the fallback LLM path."""

        self.transcriptHandler = handler

    def startPushToTalk(self, source: str = "push_to_talk") -> bool:
        """Begin a push-to-talk capture session."""

        if self.pushToTalkManager is None:
            return False
        return bool(self.pushToTalkManager.startCapture(source=source))

    def stopPushToTalk(self, asyncProcess: bool = True):
        """Stop a push-to-talk capture and transcribe the recorded audio."""

        manager = self.pushToTalkManager
        if manager is None:
            return None

        if not asyncProcess:
            return manager.stopAndProcess()

        def worker():
            try:
                manager.stopAndProcess()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Push-to-talk stop failed: {error}")

        thread = Thread(target=worker, name="AuraPushToTalkStop", daemon=True)
        thread.start()
        self._fallbackThread = thread
        return True

    def togglePushToTalk(self, source: str = "push_to_talk"):
        """Toggle capture on or off."""

        if self.isPushToTalkActive():
            return self.stopPushToTalk(asyncProcess=True)
        return self.startPushToTalk(source=source)

    def isPushToTalkActive(self) -> bool:
        """Return whether a push-to-talk capture is currently active."""

        return bool(self.pushToTalkManager and self.pushToTalkManager.isCapturing())

    def handleTranscript(self, transcript: str, source: str = "push_to_talk", result=None):
        """Route a transcribed utterance into Aura's assistant pipeline."""

        text = str(transcript or "").strip()
        if not text:
            return False

        self.lastTranscript = text
        self.lastTranscriptSource = str(source or "")
        self._emit("voice.transcript.received", {"text": text, "source": self.lastTranscriptSource})

        if self.transcriptHandler is not None:
            def invoke():
                try:
                    self.transcriptHandler(text, self.lastTranscriptSource, result)
                except Exception as error:
                    if self.logger:
                        self.logger.warning(f"Transcript handler failed: {error}")

            if self.post_ui_event is not None:
                self.post_ui_event(invoke)
            else:
                invoke()
            return True

        llm = getattr(self.context, "llm", None)
        if llm is not None and hasattr(llm, "generateResponse"):
            try:
                llm.generateResponse(text)
                return True
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Fallback voice routing failed: {error}")

        llmManager = getattr(self.context, "llmManager", None)
        if llmManager is not None and hasattr(llmManager, "generateResponse"):
            try:
                llmManager.generateResponse(text)
                return True
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Fallback LLM manager routing failed: {error}")

        return False

    def speakResponse(self, text: str):
        """Deliver assistant speech if a TTS backend exists, otherwise track the text."""

        cleaned = str(text or "").strip()
        if not cleaned:
            return {"success": False, "error": "Empty speech text."}

        self.speechQueue.enqueue(cleaned)
        try:
            if self.textToSpeech is not None and hasattr(self.textToSpeech, "speak"):
                return self.textToSpeech.speak(cleaned)
            self.lastSpokenText = cleaned
            return {"success": True, "text": cleaned, "available": False}
        finally:
            self.speechQueue.finish()

    def snapshot(self) -> dict:
        """Return voice runtime diagnostics."""

        return {
            "available": True,
            "lastTranscript": self.lastTranscript,
            "lastTranscriptSource": self.lastTranscriptSource,
            "lastSpokenText": self.lastSpokenText,
            "speechQueue": {
                "processing": bool(getattr(self.speechQueue, "_processing", False)),
                "queued": len(getattr(self.speechQueue, "_queue", [])),
            },
            "pushToTalk": self.pushToTalkManager.snapshot() if hasattr(self.pushToTalkManager, "snapshot") else {},
            "wakeWord": self.wakeWordManager.snapshot() if hasattr(self.wakeWordManager, "snapshot") else {},
        }

    def _subscribeToVoiceEvents(self):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.subscribe("presentation.voice.requested", self._onVoiceRequested)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice event subscription failed: {error}")

    def _unsubscribeFromVoiceEvents(self):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.unsubscribe("presentation.voice.requested", self._onVoiceRequested)
        except Exception:
            pass

    def _onVoiceRequested(self, event):
        payload = getattr(event, "data", {}) or {}
        text = str(payload.get("text") or "").strip()
        if not text:
            return
        try:
            self.speakResponse(text)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice delivery failed: {error}")

    def _emit(self, eventName: str, payload: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice event emission failed for {eventName}: {error}")
