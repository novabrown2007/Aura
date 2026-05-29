"""Central real-time state for the Aura Developer UI."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import RLock
from typing import Any

from interface.developerUI.models import ConsoleEvent, ConsoleStateSnapshot


class DeveloperUIState:
    """Thread-safe operational state shared by developer UI panels."""

    def __init__(self, maxEvents: int = 500):
        self.maxEvents = int(maxEvents)
        self.startedAt = datetime.now()
        self.events = deque(maxlen=self.maxEvents)
        self.sessions: dict[str, dict[str, Any]] = {}
        self.intents = deque(maxlen=200)
        self.memory = {
            "retrieved": 0,
            "injected": 0,
            "filtered": 0,
            "topMemory": "",
            "topScore": 0.0,
            "debugOutput": "",
            "storedCount": 0,
            "managerAvailable": False,
            "databasePath": "",
            "refreshError": "",
            "items": [],
        }
        self.voice = {
            "mic": "Idle",
            "recording": False,
            "stt": "Idle",
            "tts": "Idle",
            "transcription": "",
            "playback": "Idle",
            "lastTiming": {},
            "alwaysActive": {
                "state": "Unknown",
                "listening": False,
                "phrases": [],
                "confidence": 0.0,
                "lastDetection": "",
                "cooldown": False,
                "cooldownRemainingSeconds": 0.0,
                "microphone": "Unknown",
                "predictionTimeMs": 0.0,
                "activationCount": 0,
            },
            "vad": {
                "available": False,
                "enabled": False,
                "state": "IDLE",
                "speechDetected": False,
                "silenceDetected": False,
                "recordingDuration": 0.0,
                "speechDuration": 0.0,
                "silenceDuration": 0.0,
                "confidence": 0.0,
                "backend": "",
            },
        }
        self.providers = {}
        self.bridge = {"connected": False, "messages": [], "subscriptions": []}
        self.notifications = deque(maxlen=200)
        self.errors = deque(maxlen=200)
        self.system = {}
        self.conversation = {"available": False}
        self.performance = {}
        self.interruptions = {
            "available": False,
            "enabled": False,
            "active": False,
            "lastRequest": {},
            "cancelledOperations": [],
            "failedOperations": [],
        }
        self._lock = RLock()

    def recordEvent(self, event: ConsoleEvent):
        """Record one normalized event and update derived panel state."""

        with self._lock:
            self.events.append(event)
            self._applyEvent(event)

    def updateSystem(self, systemState: dict[str, Any]):
        """Update system-level state."""

        with self._lock:
            self.system = dict(systemState or {})

    def updateProviders(self, providers: dict[str, Any]):
        """Update provider state."""

        with self._lock:
            self.providers = dict(providers or {})

    def updateInterruptions(self, interruptions: dict[str, Any]):
        """Update global interruption state for the developer UI."""

        with self._lock:
            self.interruptions = dict(interruptions or {})

    def updateConversation(self, conversation: dict[str, Any]):
        """Update short-term conversational continuity state."""

        with self._lock:
            self.conversation = dict(conversation or {})

    def updateBridge(self, bridge: dict[str, Any]):
        """Update bridge state."""

        with self._lock:
            self.bridge.update(dict(bridge or {}))

    def updateMemoryDebug(self, debugOutput: str):
        """Parse and store memory retrieval debug output."""

        with self._lock:
            self.memory["debugOutput"] = str(debugOutput or "")
            for line in self.memory["debugOutput"].splitlines():
                if line.startswith("Retrieved:"):
                    self.memory["retrieved"] = self._intFromLine(line)
                elif line.startswith("Injected:"):
                    self.memory["injected"] = self._intFromLine(line)
                elif line.startswith("Filtered:"):
                    self.memory["filtered"] = self._intFromLine(line)
                elif line.startswith("Score:"):
                    try:
                        self.memory["topScore"] = float(line.split(":", 1)[1].strip())
                    except Exception:
                        self.memory["topScore"] = 0.0

    def updateMemoryStorage(
        self,
        items: list[dict[str, Any]],
        storedCount: int | None = None,
        managerAvailable: bool = True,
        databasePath: str = "",
        refreshError: str = "",
    ):
        """Store a compact snapshot of persisted structured memories."""

        with self._lock:
            cleanedItems = []
            for item in items or []:
                cleanedItems.append(
                    {
                        "category": str(item.get("category") or ""),
                        "title": str(item.get("title") or ""),
                        "content": str(item.get("content") or ""),
                        "importance": float(item.get("importance") or 0.0),
                        "source": str(item.get("source") or ""),
                        "updatedAt": str(item.get("updatedAt") or ""),
                    }
                )
            self.memory["items"] = cleanedItems
            self.memory["storedCount"] = int(storedCount if storedCount is not None else len(cleanedItems))
            self.memory["managerAvailable"] = bool(managerAvailable)
            self.memory["databasePath"] = str(databasePath or "")
            self.memory["refreshError"] = str(refreshError or "")

    def updateWakeWordState(self, wakeWordState: dict[str, Any]):
        """Update the wake word portion of the voice panel."""

        with self._lock:
            wakeWord = dict(self.voice.get("alwaysActive") or {})
            wakeWord.update(dict(wakeWordState or {}))
            self.voice["alwaysActive"] = wakeWord

    def updateVADState(self, vadState: dict[str, Any]):
        """Update voice activity detection state for the voice panel."""

        with self._lock:
            vad = dict(self.voice.get("vad") or {})
            vad.update(dict(vadState or {}))
            self.voice["vad"] = vad

    def snapshot(self) -> ConsoleStateSnapshot:
        """Return a stable snapshot for rendering."""

        with self._lock:
            uptimeSeconds = int((datetime.now() - self.startedAt).total_seconds())
            system = dict(self.system)
            system.setdefault("uptimeSeconds", uptimeSeconds)
            system.setdefault("eventCount", len(self.events))
            return ConsoleStateSnapshot(
                events=[event.asDict() for event in list(self.events)],
                sessions=list(self.sessions.values()),
                intents=list(self.intents),
                memory=dict(self.memory),
                voice=dict(self.voice),
                providers=dict(self.providers),
                bridge=dict(self.bridge),
                notifications=list(self.notifications),
                errors=list(self.errors),
                system=system,
                performance=dict(self.performance),
                interruptions=dict(self.interruptions),
                conversation=dict(self.conversation),
            )

    def _applyEvent(self, event: ConsoleEvent):
        name = event.name
        payload = event.payload or {}
        if name in {"session.created", "conversation.started"}:
            sessionId = str(payload.get("sessionId") or payload.get("session_id") or payload.get("conversationId") or "default")
            self.sessions[sessionId] = {
                "sessionId": sessionId,
                "interface": payload.get("interface", ""),
                "startedAt": event.timestamp,
                "context": payload,
            }
        elif name in {"session.ended", "conversation.ended"}:
            sessionId = str(payload.get("sessionId") or payload.get("session_id") or payload.get("conversationId") or "default")
            self.sessions.pop(sessionId, None)
        elif "intent" in name:
            self.intents.append({"timestamp": event.timestamp, "name": name, "payload": payload})
        elif name.startswith("voice.capture.started"):
            self.voice.update({"mic": "Recording", "recording": True})
        elif name.startswith("voice.capture.finished"):
            self.voice.update({"mic": "Idle", "recording": False})
        elif name.startswith("voice.transcription.started"):
            self.voice["stt"] = "Processing"
        elif name.startswith("voice.transcription.completed"):
            self.voice["stt"] = "Idle"
            self.voice["transcription"] = str(payload.get("text") or "")
            self.voice["lastTiming"] = {"audioDuration": payload.get("audioDuration")}
        elif name == "tts.started":
            self.voice["tts"] = "Speaking"
        elif name == "tts.finished":
            self.voice["tts"] = "Idle"
            self.voice["playback"] = "Finished" if payload.get("success", True) else "Failed"
        elif name == "tts.cancelled":
            self.voice["tts"] = "Cancelled"
            self.voice["playback"] = "Cancelled"
            self._applyInterruptionEvent(name, payload, event.timestamp)
        elif name.startswith("interruption.") or name.endswith(".cancelled") or name == "operation.cancelled":
            self._applyInterruptionEvent(name, payload, event.timestamp)
        elif name.startswith("wakeword."):
            self._applyWakeWordEvent(name, payload, event.timestamp)
        elif name.startswith("vad."):
            self._applyVADEvent(name, payload)
        elif name.startswith("memory.") or "memory" in name:
            debugOutput = payload.get("debugOutput") or payload.get("debug") or ""
            if debugOutput:
                self.updateMemoryDebug(debugOutput)
        elif name.startswith("bridge.") or "bridge" in name:
            messages = list(self.bridge.get("messages") or [])
            messages.append(event.asDict())
            self.bridge["messages"] = messages[-100:]
            if "connected" in payload:
                self.bridge["connected"] = bool(payload.get("connected"))
        elif name.startswith("notification") or "notification" in name:
            self.notifications.append({"timestamp": event.timestamp, "name": name, "payload": payload})
        if event.error or "error" in name or payload.get("error") or payload.get("errorMessage"):
            self.errors.append({"timestamp": event.timestamp, "name": name, "payload": payload, "error": event.error or payload.get("error") or payload.get("errorMessage")})

    @staticmethod
    def _intFromLine(line: str) -> int:
        try:
            return int(line.split(":", 1)[1].strip().split()[0])
        except Exception:
            return 0

    def _applyWakeWordEvent(self, name: str, payload: dict[str, Any], timestamp: str):
        wakeWord = dict(self.voice.get("alwaysActive") or {})
        wakeWord["confidence"] = float(payload.get("confidence") or wakeWord.get("confidence") or 0.0)
        wakeWord["predictionTimeMs"] = float(payload.get("predictionTimeMs") or wakeWord.get("predictionTimeMs") or 0.0)
        wakeWord["activationCount"] = int(payload.get("activationCount") or wakeWord.get("activationCount") or 0)
        if name == "wakeword.listening.started":
            wakeWord.update({"state": "Listening", "listening": True, "microphone": "Open"})
        elif name == "wakeword.listening.stopped":
            wakeWord.update({"state": "Idle", "listening": False, "microphone": "Closed"})
        elif name == "wakeword.detected":
            wakeWord.update({"state": "Detected", "listening": False, "lastDetection": timestamp})
        elif name == "wakeword.cooldown.started":
            wakeWord.update(
                {
                    "state": "Cooldown",
                    "listening": False,
                    "cooldown": True,
                    "cooldownRemainingSeconds": float(payload.get("cooldownSeconds") or 0.0),
                    "microphone": "Paused",
                }
            )
        elif name == "wakeword.cooldown.finished":
            wakeWord.update({"state": "Idle", "cooldown": False, "cooldownRemainingSeconds": 0.0})
        elif name == "wakeword.error":
            wakeWord.update({"state": "Error", "listening": False, "microphone": "Unavailable"})
        self.voice["alwaysActive"] = wakeWord

    def _applyInterruptionEvent(self, name: str, payload: dict[str, Any], timestamp: str):
        interruptions = dict(self.interruptions or {})
        interruptions.update({"available": True, "enabled": True, "lastEvent": name, "lastUpdated": timestamp})
        if name == "interruption.started":
            interruptions["active"] = True
            interruptions["lastRequest"] = payload.get("request", payload)
            interruptions["cancelledOperations"] = []
            interruptions["failedOperations"] = []
        elif name == "interruption.completed":
            interruptions["active"] = False
            interruptions["lastRequest"] = payload.get("request", interruptions.get("lastRequest", {}))
            interruptions["cancelledOperations"] = list(payload.get("interruptedOperations") or payload.get("cancelledOperations") or [])
            interruptions["failedOperations"] = list(payload.get("failedOperations") or [])
            interruptions["durationMs"] = float(payload.get("durationMs") or 0.0)
        elif name == "interruption.failed":
            interruptions["active"] = False
            interruptions["failedOperations"] = list(payload.get("failedOperations") or [])
        elif name == "operation.cancelled":
            cancelled = list(interruptions.get("cancelledOperations") or [])
            operationId = payload.get("operationId")
            if operationId and operationId not in cancelled:
                cancelled.append(operationId)
            interruptions["cancelledOperations"] = cancelled
        elif name.endswith(".cancelled"):
            cancelled = list(interruptions.get("cancelledOperations") or [])
            operationId = payload.get("operationId") or name
            if operationId and operationId not in cancelled:
                cancelled.append(operationId)
            interruptions["cancelledOperations"] = cancelled
        self.interruptions = interruptions

    def _applyVADEvent(self, name: str, payload: dict[str, Any]):
        vad = dict(self.voice.get("vad") or {})
        vad.update(dict(payload or {}))
        if name == "vad.started":
            vad.update({"state": "LISTENING", "active": True})
            self.voice.update({"mic": "Listening", "recording": True})
        elif name == "vad.speech.detected":
            vad.update({"state": "SPEAKING", "speechDetected": True})
            self.voice.update({"mic": "Speaking", "recording": True})
        elif name == "vad.silence.detected":
            vad.update({"state": "SILENCE_PENDING", "silenceDetected": True})
            self.voice.update({"mic": "Silence pending", "recording": True})
        elif name in {"vad.speech.completed", "vad.timeout", "vad.finalizing"}:
            vad.update({"state": "FINALIZING", "active": False})
            self.voice.update({"mic": "Finalizing", "recording": True})
        elif name == "vad.error":
            vad.update({"state": "ERROR", "active": False})
        self.voice["vad"] = vad
