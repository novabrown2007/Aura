"""Runtime diagnostics and execution tracing for Aura."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any


class ObservabilityManager:
    """
    Read-only diagnostics facade for Aura runtime subsystems.

    The manager collects current runtime state for threads, logs, events,
    memory, tools, providers, module health, execution traces, and scheduler
    jobs. It also stores a bounded in-memory trace stream for recent execution
    activity.
    """

    def __init__(self, context, max_traces: int = 500):
        """Initialize the diagnostics facade."""

        self.context = context
        self.max_traces = int(max_traces)
        self.traces = deque(maxlen=self.max_traces)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Observability") if hasattr(logger, "getChild") else None

    def recordTrace(self, trace_type: str, name: str, status: str = "ok", details: dict | None = None):
        """Record a single runtime trace entry."""

        entry = {
            "timestamp": self._now(),
            "type": str(trace_type),
            "name": str(name),
            "status": str(status),
            "details": details or {},
        }
        self.traces.append(entry)
        return entry

    def snapshot(self):
        """Return a complete observability snapshot."""

        return {
            "threads": self.getThreads(),
            "logs": self.getLogs(),
            "events": self.getEvents(),
            "memory": self.getMemoryState(),
            "tools": self.getTools(),
            "providers": self.getProviders(),
            "modules": self.getModuleHealth(),
            "traces": self.getTraces(),
            "scheduler": self.getSchedulerState(),
            "interruptions": self.getInterruptionState(),
            "conversation": self.getConversationState(),
            "vad": self.getVADState(),
            "personality": self.getPersonalityState(),
        }

    def getThreads(self):
        """Return managed thread state."""

        threader = getattr(self.context, "threader", None)
        if threader is None:
            return []

        threads = []
        for name, thread in getattr(threader, "threads", {}).items():
            control = getattr(threader, "controls", {}).get(name)
            threads.append(
                {
                    "name": name,
                    "alive": thread.is_alive(),
                    "daemon": thread.daemon,
                    "paused": bool(control and not control.pause_event.is_set()),
                    "stop_requested": bool(control and control.stop_event.is_set()),
                }
            )
        return threads

    def getLogs(self, lines: int = 50):
        """Return current log file metadata and recent lines."""

        logger = getattr(self.context, "logger", None)
        log_path = getattr(logger, "logFilePath", None)
        if log_path is None:
            return {"path": None, "lines": []}

        path = Path(log_path)
        if not path.exists():
            return {"path": str(path), "lines": []}

        return {
            "path": str(path),
            "lines": path.read_text(encoding="utf-8", errors="replace").splitlines()[-int(lines):],
        }

    def getEvents(self):
        """Return event listener counts."""

        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is None:
            return {}

        return {
            name: event_manager.listenerCount(name)
            for name in event_manager.listEvents()
        }

    def getMemoryState(self):
        """Return memory counts and keys without expanding every value."""

        memory_manager = getattr(self.context, "memoryManager", None)
        if memory_manager is None or not hasattr(memory_manager, "getMemory"):
            return {"available": False, "count": 0, "keys": []}

        memory = memory_manager.getMemory()
        return {
            "available": True,
            "count": len(memory),
            "keys": sorted(str(key) for key in memory.keys()),
        }

    def getTools(self):
        """Return registered deterministic tools."""

        registry = getattr(self.context, "toolRegistry", None)
        if registry is None:
            return []

        return [
            tool.asDict() if hasattr(tool, "asDict") else {"name": name}
            for name, tool in sorted(registry.tools.items())
        ]

    def getProviders(self):
        """Return LLM provider status."""

        manager = getattr(self.context, "llmManager", None)
        if manager is None:
            return {"available": False, "providers": {}}

        status = manager.getStatus() if hasattr(manager, "getStatus") else {}
        providers = {}
        activeProviderName = status.get("activeProvider") or getattr(manager, "activeProviderName", None)
        preferredProviderName = status.get("preferredProvider") or getattr(manager, "preferredProviderName", activeProviderName)
        fallbackProviderName = status.get("fallbackProvider") or getattr(manager, "fallbackProviderName", None)
        activeModel = ""
        for name, provider in getattr(manager, "providers", {}).items():
            model = str(getattr(provider, "model", "") or "")
            if name == activeProviderName:
                activeModel = model
            providers[name] = {
                "initialized": bool(getattr(provider, "initialized", False)),
                "active": name == activeProviderName,
                "fallback": name == fallbackProviderName,
                "model": model,
            }

        voice = getattr(self.context, "voiceManager", None)
        stt = {}
        tts = {}
        if voice is not None:
            stt = {
                "provider": "faster-whisper",
                "model": str(getattr(voice, "inputModelName", "") or ""),
                "enabled": bool(getattr(voice, "inputEnabled", False)),
                "initialized": bool(getattr(getattr(voice, "speechToText", None), "initialized", False)),
                "device": str(getattr(voice, "inputDevice", "") or ""),
                "computeType": str(getattr(voice, "inputComputeType", "") or ""),
            }
            tts = {
                "provider": "piper",
                "model": str(getattr(voice, "outputModelPath", "") or ""),
                "enabled": bool(getattr(voice, "outputEnabled", False)),
                "initialized": bool(getattr(getattr(voice, "textToSpeech", None), "initialized", False)),
                "playbackEnabled": bool(getattr(voice, "playbackEnabled", False)),
            }

        return {
            "available": True,
            "offlineMode": bool(status.get("offlineMode", getattr(manager, "offlineMode", False))),
            "activeProvider": str(activeProviderName or ""),
            "activeModel": activeModel or str(activeProviderName or "Unknown"),
            "preferredProvider": str(preferredProviderName or ""),
            "preferredModel": str(status.get("preferredModel") or ""),
            "fallbackProvider": str(fallbackProviderName or ""),
            "offlineReason": str(status.get("offlineReason") or ""),
            "canUseStructuredOutput": bool(status.get("canUseStructuredOutput", True)),
            "providers": providers,
            "voice": {
                "stt": stt,
                "tts": tts,
            },
        }

    def getConversationState(self):
        """Return short-term conversational continuity state."""

        manager = getattr(self.context, "conversationManager", None)
        if manager is None or not hasattr(manager, "snapshot"):
            return {"available": False}
        try:
            snapshot = manager.snapshot()
            snapshot["available"] = True
            return snapshot
        except Exception as error:
            return {"available": False, "error": str(error)}

    def getVADState(self):
        """Return voice activity detection diagnostics."""

        manager = getattr(self.context, "vadManager", None)
        if manager is None or not hasattr(manager, "snapshot"):
            return {"available": False, "enabled": False}
        try:
            return manager.snapshot()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"VAD snapshot failed: {error}")
            return {"available": False, "enabled": False, "error": str(error)}

    def getPersonalityState(self):
        """Return controlled personality diagnostics."""

        manager = getattr(self.context, "personalityManager", None)
        if manager is None or not hasattr(manager, "snapshot"):
            return {"available": False, "enabled": False}
        try:
            return manager.snapshot()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Personality snapshot failed: {error}")
            return {"available": False, "enabled": False, "error": str(error)}

    def getModuleHealth(self):
        """Return loaded/discovered module health metadata."""

        loader = getattr(self.context, "moduleLoader", None) or getattr(self.context, "moduleManager", None)
        context_modules = getattr(self.context, "modules", {}) or {}
        if loader is None:
            return {
                name: {"loaded": True, "class": module.__class__.__name__}
                for name, module in sorted(context_modules.items())
            }

        health = {}
        descriptors = getattr(loader, "descriptors", {}) or {}
        loaded = getattr(loader, "loadedModules", {}) or {}
        disabled = getattr(loader, "disabledModules", set()) or set()
        registry = getattr(loader, "registry", None)

        for name, descriptor in sorted(descriptors.items()):
            module = loaded.get(name)
            metadata = getattr(descriptor, "metadata", None)
            if metadata is None and registry is not None and name in getattr(registry, "entries", {}):
                metadata = registry.entries[name].metadata
            health[name] = {
                "enabled": bool(getattr(descriptor, "enabled", False)),
                "loaded": module is not None,
                "disabled": name in disabled,
                "version": getattr(metadata, "version", ""),
                "capabilities": list(getattr(metadata, "capabilities", ())),
                "intents": len(getattr(registry.entries.get(name), "intents", [])) if registry is not None and name in getattr(registry, "entries", {}) else 0,
                "actions": len(getattr(registry.entries.get(name), "actions", [])) if registry is not None and name in getattr(registry, "entries", {}) else 0,
                "state": registry.entries[name].state.value if registry is not None and name in getattr(registry, "entries", {}) else None,
                "class": module.__class__.__name__ if module is not None else None,
            }

        for name, module in sorted(context_modules.items()):
            health.setdefault(
                name,
                {"enabled": True, "loaded": True, "disabled": False, "class": module.__class__.__name__},
            )

        return health

    def getTraces(self, limit: int | None = None):
        """Return recent execution traces."""

        traces = list(self.traces)
        if limit is not None:
            return traces[-int(limit):]
        return traces

    def getSchedulerState(self):
        """Return scheduler and schedule state."""

        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is None:
            return {"available": False, "running": False, "schedules": []}

        schedules = []
        for name, schedule in sorted(getattr(scheduler, "schedules", {}).items()):
            schedules.append(
                {
                    "name": name,
                    "enabled": bool(schedule.enabled),
                    "interval": schedule.interval,
                    "run_at": schedule.run_at,
                    "last_run": schedule.last_run,
                }
            )

        return {
            "available": True,
            "running": bool(getattr(scheduler, "running", False)),
            "tick_interval": getattr(scheduler, "tick_interval", None),
            "schedules": schedules,
        }

    def getInterruptionState(self):
        """Return global interruption and cancellation diagnostics."""

        manager = getattr(self.context, "interruptionManager", None)
        if manager is None or not hasattr(manager, "snapshot"):
            return {"available": False, "enabled": False}
        try:
            snapshot = manager.snapshot()
            snapshot["available"] = True
            return snapshot
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Interruption snapshot failed: {error}")
            return {"available": False, "enabled": False, "error": str(error)}

    def _now(self):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
