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
        }
        self.providers = {}
        self.bridge = {"connected": False, "messages": [], "subscriptions": []}
        self.notifications = deque(maxlen=200)
        self.errors = deque(maxlen=200)
        self.system = {}
        self.performance = {}
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

    def updateMemoryStorage(self, items: list[dict[str, Any]], storedCount: int | None = None):
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
