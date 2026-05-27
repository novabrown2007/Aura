"""Developer UI subscriptions to Aura runtime systems."""

from __future__ import annotations


class UISubscriptionManager:
    """Subscribe developer UI state to key Aura event bus updates."""

    defaultEvents = (
        "voice.capture.started",
        "voice.capture.finished",
        "voice.transcription.started",
        "voice.transcription.completed",
        "conversation.message.received",
        "message.received",
        "intent.generated",
        "response.generated",
        "tts.started",
        "tts.finished",
        "voice.loop.completed",
        "voice.loop.failed",
        "session.created",
        "session.ended",
        "conversation.started",
        "conversation.ended",
        "bridge.connected",
        "bridge.disconnected",
        "assistant.notification",
        "notification.created",
        "memory.retrieval.completed",
        "memory.injected",
        "provider.request.completed",
        "provider.request.failed",
        "error",
    )

    def __init__(self, context, state, tracer=None):
        self.context = context
        self.state = state
        self.tracer = tracer
        self.subscribed = False
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Subscriptions") if logger else None

    def subscribe(self):
        """Subscribe to known event names when an event manager exists."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or self.subscribed:
            return
        for eventName in self.defaultEvents:
            try:
                eventManager.subscribe(eventName, self.handleEvent)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Developer UI subscription failed for {eventName}: {error}")
        self.subscribed = True

    def unsubscribe(self):
        """Remove event subscriptions."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or not self.subscribed:
            return
        for eventName in self.defaultEvents:
            try:
                eventManager.unsubscribe(eventName, self.handleEvent)
            except Exception:
                pass
        self.subscribed = False

    def handleEvent(self, event):
        """Route one Aura event into UI state."""

        if self.tracer is not None and not getattr(self.tracer, "installed", False):
            self.tracer.trace(getattr(event, "name", ""), getattr(event, "data", {}) or {})

    def refreshSubsystemState(self):
        """Pull read-only subsystem snapshots for panels that are not purely event-driven."""

        try:
            observability = getattr(self.context, "observability", None)
            if observability is not None:
                snapshot = observability.snapshot()
                self.state.updateSystem(
                    {
                        "events": snapshot.get("events", {}),
                        "modules": snapshot.get("modules", {}),
                        "threads": snapshot.get("threads", []),
                        "scheduler": snapshot.get("scheduler", {}),
                    }
                )
                self.state.updateProviders(snapshot.get("providers", {}))
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Developer UI observability refresh failed: {error}")

        try:
            memory = getattr(self.context, "memoryManager", None)
            if memory is None:
                self.state.updateMemoryStorage([], storedCount=0, managerAvailable=False)
            else:
                debugOutput = getattr(memory, "lastRetrievalDebug", "") if memory is not None else ""
                if debugOutput:
                    self.state.updateMemoryDebug(debugOutput)
                databasePath = ""
                store = getattr(memory, "store", None)
                if store is not None:
                    databasePath = str(getattr(store, "databasePath", "") or "")
                if hasattr(memory, "retrieveMemories"):
                    memories = self._loadStoredMemories(memory, limit=10)
                    items = []
                    for item in memories:
                        items.append(
                            {
                                "category": getattr(item, "category", ""),
                                "title": getattr(item, "title", ""),
                                "content": getattr(item, "content", ""),
                                "importance": getattr(item, "importance", 0.0),
                                "source": getattr(item, "source", ""),
                                "updatedAt": getattr(item, "updatedAt", ""),
                            }
                        )
                    self.state.updateMemoryStorage(
                        items,
                        storedCount=len(items),
                        managerAvailable=True,
                        databasePath=databasePath,
                    )
                else:
                    self.state.updateMemoryStorage(
                        [],
                        storedCount=0,
                        managerAvailable=True,
                        databasePath=databasePath,
                        refreshError="Memory manager does not expose retrieveMemories().",
                    )
        except Exception as error:
            self.state.updateMemoryStorage([], storedCount=0, managerAvailable=False, refreshError=str(error))
            if self.logger:
                self.logger.warning(f"Developer UI memory refresh failed: {error}")

        try:
            bridge = getattr(self.context, "bridgeStateCache", None)
            if bridge is not None and hasattr(bridge, "snapshot"):
                self.state.updateBridge(bridge.snapshot())
        except Exception:
            pass

    @staticmethod
    def _loadStoredMemories(memory, limit=10):
        """Read memory rows for display without triggering retrieval scoring logs."""

        store = getattr(memory, "store", None)
        if store is not None and hasattr(store, "queryMemories"):
            try:
                from modules.llm.memory.models.memoryQuery import MemoryQuery

                return store.queryMemories(MemoryQuery(limit=limit))
            except Exception:
                pass
        return memory.retrieveMemories(limit=limit)
