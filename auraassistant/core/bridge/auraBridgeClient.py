"""Transport-facing Aura Protocol client for assistant cognition."""

from __future__ import annotations

import json
from threading import Event, Lock
from typing import Any
from urllib import error, parse, request

from modules.home_automation.config import BridgeConfig, HomeAutomationConfig
from modules.home_automation.models import BridgeState, CameraDevice, Device, HomeAutomationNotification, LightDevice

from .handlers.contextHandler import ContextHandler
from .handlers.errorHandler import ErrorHandler
from .handlers.notificationHandler import NotificationHandler
from .handlers.responseHandler import ResponseHandler
from .handlers.streamHandler import StreamHandler
from .intents.intentBridgeAdapter import IntentBridgeAdapter
from .intents.intentRequestBuilder import IntentRequestBuilder
from .notifications.notificationManager import NotificationManager
from .protocol.auraCategories import AuraCategories
from .protocol.auraMessage import AuraMessage
from .routing.auraRouter import AuraRouter
from .serialization.auraSerializer import AuraSerializer
from .sessions.auraSessionManager import AuraSessionManager
from .state.bridgeStateCache import BridgeStateCache
from .streams.streamManager import StreamManager
from .streams.streamRegistry import StreamRegistry
from .subscriptions.auraSubscriptionManager import AuraSubscriptionManager
from .validation.auraValidator import AuraValidator


class HttpAuraProtocolTransport:
    """Standard-library HTTP transport for the Aura Protocol."""

    def __init__(self, baseUrl: str, timeoutSeconds: float = 5.0, protocolPath: str = "/protocol/aura", inboxPath: str = "/protocol/inbox", subscriptionsPath: str = "/protocol/subscriptions", heartbeatPath: str = "/protocol/heartbeat"):
        self.baseUrl = baseUrl.rstrip("/")
        self.timeoutSeconds = float(timeoutSeconds)
        self.protocolPath = protocolPath
        self.inboxPath = inboxPath
        self.subscriptionsPath = subscriptionsPath
        self.heartbeatPath = heartbeatPath

    def send(self, message: AuraMessage | dict[str, Any]) -> dict[str, Any]:
        """POST one protocol message."""

        return self._request("POST", self.protocolPath, message)

    def receive(self, sessionId: str = "", categories: list[str] | None = None, since: str = "") -> dict[str, Any]:
        """Poll protocol messages for a session."""

        query = {}
        if sessionId:
            query["sessionId"] = sessionId
        if categories:
            query["categories"] = ",".join(categories)
        if since:
            query["since"] = since
        path = self.inboxPath
        if query:
            path = f"{path}?{parse.urlencode(query)}"
        return self._request("GET", path, None)

    def subscribe(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Register one subscription payload."""

        return self._request("POST", self.subscriptionsPath, payload)

    def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a deterministic heartbeat message."""

        return self._request("POST", self.heartbeatPath, payload)

    def _request(self, method: str, path: str, payload: AuraMessage | dict[str, Any] | None):
        """Send one JSON request to the bridge protocol endpoint."""

        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload.toDict() if isinstance(payload, AuraMessage) else payload, ensure_ascii=True).encode("utf-8")
            headers["Content-Type"] = "application/json"

        bridge_request = request.Request(
            url=f"{self.baseUrl}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(bridge_request, timeout=self.timeoutSeconds) as response:
                raw_body = response.read().decode("utf-8")
        except error.URLError as exception:
            reason = getattr(exception, "reason", exception)
            raise ConnectionError(f"Failed to reach Aura Protocol bridge at {self.baseUrl}: {reason}") from exception
        except OSError as exception:
            raise ConnectionError(f"Aura Protocol bridge request failed: {exception}") from exception

        if not raw_body:
            return {}

        parsed = json.loads(raw_body)
        if isinstance(parsed, dict):
            return parsed
        return {"messages": parsed}


class AuraBridgeClient:
    """Bridge-side transport and routing client for Aura."""

    def __init__(self, context=None, transport=None):
        self.context = context
        self.logger = None
        self.transport = transport
        self.validator = AuraValidator()
        self.sessionManager = AuraSessionManager(context)
        self.subscriptionManager = AuraSubscriptionManager(context)
        self.notificationManager = NotificationManager(context)
        self.streamRegistry = StreamRegistry(context)
        self.streamManager = StreamManager(context, registry=self.streamRegistry)
        self.stateCache = BridgeStateCache(context)
        self.requestBuilder = IntentRequestBuilder(context, self.sessionManager)
        self.intentAdapter = IntentBridgeAdapter(context, self, self.requestBuilder, validator=self.validator)
        self.router = AuraRouter(context, validator=self.validator)
        self.pendingRequests: dict[str, Event] = {}
        self.pendingPayloads: dict[str, dict[str, Any]] = {}
        self.pendingLock = Lock()
        self.connected = False
        self.initialized = False
        self.bridgeConfig = None

        if context is not None:
            self.initialize(context)

    def initialize(self, context=None):
        """Bind the client to runtime services and prepare routing state."""

        if context is not None:
            self.context = context

        self.logger = self._getLogger("AuraBridge")
        self.bridgeConfig = self._resolveBridgeConfig()
        self.transport = self.transport or HttpAuraProtocolTransport(
            baseUrl=self.bridgeConfig.base_url,
            timeoutSeconds=self.bridgeConfig.timeout_seconds,
            protocolPath=self.bridgeConfig.protocol_path,
            inboxPath=self.bridgeConfig.inbox_path,
            subscriptionsPath=self.bridgeConfig.subscriptions_path,
            heartbeatPath=self.bridgeConfig.heartbeat_path,
        )

        if self.context is not None:
            self.context.bridgeClient = self
            self.context.auraBridgeClient = self
            self.context.bridgeStateCache = self.stateCache
            self.context.bridgeNotificationManager = self.notificationManager
            self.context.bridgeStreamManager = self.streamManager
            self.context.bridgeSessionManager = self.sessionManager
            self.context.bridgeSubscriptionManager = self.subscriptionManager
            self.context.bridgeRouter = self.router

            self.context.contextHandler = ContextHandler(self.context, self.stateCache)
            self.context.notificationHandler = NotificationHandler(self.context, self.notificationManager, self.stateCache)
            self.context.responseHandler = ResponseHandler(self.context, self.stateCache)
            self.context.errorHandler = ErrorHandler(self.context, self.stateCache)
            self.context.streamHandler = StreamHandler(self.context, self.streamManager, self.stateCache)

        self.router.registerDefaultHandlers()
        self.initialized = True
        if self.logger:
            self.logger.info("Aura bridge client initialized.")
        return self

    def connect(self):
        """Mark the bridge client connected and prime default subscriptions."""

        self.ensureSession(interface=self.bridgeConfig.interface_name, sessionId=self._configuredSessionId())
        self.subscribeDefaultCategories()
        self.syncContext(interface=self.bridgeConfig.interface_name, sessionId=self._configuredSessionId())
        self.connected = True
        self.stateCache.connected = True
        return self.stateCache.snapshot()

    def disconnect(self):
        """Mark the bridge client disconnected."""

        self.connected = False
        self.stateCache.connected = False

    def ensureSession(self, interface: str = "desktop", sessionId: str | None = None):
        """Create or return one active assistant session."""

        if sessionId is None:
            sessionId = self._configuredSessionId()
        if not interface:
            interface = self.bridgeConfig.interface_name
        session = self.sessionManager.getSession(sessionId)
        if session is None:
            session = self.sessionManager.createSession(interface=interface, sessionId=sessionId)
        return session

    def subscribeDefaultCategories(self):
        """Subscribe to the core assistant-facing categories."""

        categories = [
            AuraCategories.ASSISTANT_NOTIFICATION,
            AuraCategories.ASSISTANT_RESPONSE,
            AuraCategories.ASSISTANT_ERROR,
            AuraCategories.ASSISTANT_STREAM_AVAILABLE,
            AuraCategories.ASSISTANT_CONTEXT,
        ]
        session = self.ensureSession(interface=self.bridgeConfig.interface_name)
        if not categories:
            return []

        subscriptions = []
        for category in categories:
            subscription = self.subscriptionManager.subscribe(
                categories=[category],
                interface=session.interface,
                sessionId=session.sessionId,
            )
            subscriptions.append(subscription)
            try:
                self.transport.subscribe(
                    {
                        "subscriptionId": subscription.subscriptionId,
                        "categories": list(subscription.categories),
                        "interface": subscription.interface,
                        "sessionId": subscription.sessionId,
                        "wildcard": subscription.wildcard,
                        "metadata": subscription.metadata,
                    }
                )
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Bridge subscription failed for {category}: {error}")
        return subscriptions

    def sendMessage(self, message: AuraMessage | dict[str, Any]):
        """Validate, serialize, and send one bridge message."""

        if not hasattr(message, "toDict"):
            message = AuraMessage.fromDict(message)

        valid, error = self.validator.validateMessage(message)
        if not valid:
            raise ValueError(f"{error.code}: {error.message}")

        self._registerPending(message)
        try:
            response = self.transport.send(message)
        except Exception as error:
            self._finalizePending(message.requestId or message.messageId, success=False, error=str(error))
            if self.logger:
                self.logger.error(f"Bridge send failed: {error}")
            raise

        self._processTransportPayload(response)
        self._finalizePending(message.requestId or message.messageId, success=True, response=response)
        return response

    def receiveMessages(self, sessionId: str = "", categories: list[str] | None = None, since: str = "") -> list[AuraMessage]:
        """Pull one batch of inbound protocol messages."""

        response = self.transport.receive(sessionId=sessionId, categories=categories, since=since)
        return self._normalizeMessages(response)

    def poll(self):
        """Receive and route any available inbound messages."""

        session = self.sessionManager.getActiveSession()
        messages = self.receiveMessages(sessionId=session.sessionId if session else "")
        return self.processMessages(messages)

    def processMessages(self, messages):
        """Route a collection of inbound protocol messages."""

        routed = []
        for message in messages:
            result = self.router.route(message)
            routed.append(result)
        return routed

    def syncContext(self, extraContext: dict[str, Any] | None = None, sessionId: str | None = None, interface: str = "desktop"):
        """Send assistant context to the bridge."""

        message = self.requestBuilder.buildContextRequest(
            sessionId=sessionId,
            interface=interface,
            contextData=extraContext or {},
        )
        return self.sendMessage(message)

    def submitIntent(self, intent, sessionId: str | None = None, interface: str = "desktop", extraContext: dict[str, Any] | None = None):
        """Submit one structured intent through the bridge adapter."""

        return self.intentAdapter.submitIntent(intent, sessionId=sessionId, interface=interface, extraContext=extraContext)

    def submitIntents(self, intents: list[Any], sessionId: str | None = None, interface: str = "desktop", extraContext: dict[str, Any] | None = None):
        """Submit multiple ordered intents through the bridge adapter."""

        return self.intentAdapter.submitIntents(intents, sessionId=sessionId, interface=interface, extraContext=extraContext)

    def completePendingRequest(self, requestId: str, payload: dict[str, Any]):
        """Release one pending request waiter."""

        with self.pendingLock:
            event = self.pendingRequests.get(requestId)
            if event is not None:
                self.pendingPayloads[requestId] = payload
                event.set()

    def waitForResponse(self, requestId: str, timeoutSeconds: float = 5.0) -> dict[str, Any] | None:
        """Wait for a matching assistant.response payload."""

        with self.pendingLock:
            event = self.pendingRequests.get(requestId)
        if event is None:
            return self.stateCache.getResponse(requestId)
        if not event.wait(timeoutSeconds):
            return None
        return self.pendingPayloads.get(requestId) or self.stateCache.getResponse(requestId)

    def getBridgeState(self) -> BridgeState:
        """Return a compatibility snapshot for the home automation module."""

        snapshot = self.stateCache.snapshot()
        return self._buildBridgeState(snapshot)

    def refreshDevices(self) -> BridgeState:
        """Request a fresh context snapshot from the bridge."""

        try:
            self.syncContext({"request": "bridgeState", "include": ["devices", "lights", "cameras", "notifications", "streams"]})
        except Exception as error:
            self.stateCache.lastError = str(error)
            if self.logger:
                self.logger.warning(f"Bridge refresh failed: {error}")
        return self.getBridgeState()

    def getDevices(self) -> list[Device]:
        """Return known devices from the cached bridge state."""

        return self.getBridgeState().devices

    def getLights(self) -> list[LightDevice]:
        """Return known lights from the cached bridge state."""

        return self.getBridgeState().lights

    def getCameras(self) -> list[CameraDevice]:
        """Return known cameras from the cached bridge state."""

        return self.getBridgeState().cameras

    def setLightState(self, deviceId: str, isOn: bool, brightness: int | None = None) -> LightDevice:
        """Request a deterministic light state change through the bridge."""

        intent = {
            "intent": "lights.turnOn" if isOn else "lights.turnOff",
            "confidence": 1.0,
            "arguments": {"device_id": deviceId, "is_on": bool(isOn)},
        }
        if brightness is not None:
            intent["arguments"]["brightness"] = int(brightness)
        self.submitIntent(intent)
        if brightness is not None and isOn:
            return self.setLightBrightness(deviceId, brightness)
        return self._findLight(deviceId, f"Light '{deviceId}' is not available.")

    def setLightBrightness(self, deviceId: str, brightness: int) -> LightDevice:
        """Request a bridge-owned brightness update."""

        self.submitIntent(
            {
                "intent": "lights.setBrightness",
                "confidence": 1.0,
                "arguments": {"device_id": deviceId, "brightness": int(brightness)},
            }
        )
        return self._findLight(deviceId, f"Light '{deviceId}' missing after brightness update.")

    def setLightTemperature(self, deviceId: str, kelvin: int) -> LightDevice:
        """Request a bridge-owned temperature update."""

        self.submitIntent(
            {
                "intent": "lights.setTemperature",
                "confidence": 1.0,
                "arguments": {"device_id": deviceId, "kelvin": int(kelvin)},
            }
        )
        return self._findLight(deviceId, f"Light '{deviceId}' missing after temperature update.")

    def setLightColor(self, deviceId: str, color: str) -> LightDevice:
        """Request a bridge-owned color update."""

        self.submitIntent(
            {
                "intent": "lights.setColor",
                "confidence": 1.0,
                "arguments": {"device_id": deviceId, "color": str(color)},
            }
        )
        return self._findLight(deviceId, f"Light '{deviceId}' missing after color update.")

    def startCameraStream(self, deviceId: str) -> CameraDevice:
        """Request a bridge-owned camera stream start."""

        self.submitIntent(
            {
                "intent": "camera.startStream",
                "confidence": 1.0,
                "arguments": {"device_id": deviceId},
            }
        )
        return self._findCamera(deviceId, f"Camera '{deviceId}' missing after start stream.")

    def stopCameraStream(self, deviceId: str) -> CameraDevice:
        """Request a bridge-owned camera stream stop."""

        self.submitIntent(
            {
                "intent": "camera.stopStream",
                "confidence": 1.0,
                "arguments": {"device_id": deviceId},
            }
        )
        return self._findCamera(deviceId, f"Camera '{deviceId}' missing after stop stream.")

    def takeCameraSnapshot(self, deviceId: str) -> CameraDevice:
        """Request a bridge-owned camera snapshot."""

        self.submitIntent(
            {
                "intent": "camera.takeSnapshot",
                "confidence": 1.0,
                "arguments": {"device_id": deviceId},
            }
        )
        return self._findCamera(deviceId, f"Camera '{deviceId}' missing after snapshot.")

    def listNotifications(self) -> list[HomeAutomationNotification]:
        """Return normalized bridge notifications for compatibility callers."""

        notifications = []
        for item in self.stateCache.getNotificationContext():
            notifications.append(
                HomeAutomationNotification(
                    notification_id=str(item.get("notification_id") or item.get("id") or item.get("messageId") or ""),
                    source=str(item.get("source") or ""),
                    severity=str(item.get("severity") or "info"),
                    category=str(item.get("category") or "system"),
                    title=str(item.get("title") or item.get("event") or ""),
                    message=str(item.get("message") or item.get("content") or ""),
                    device_id=str(item.get("device_id") or ""),
                    created_at=str(item.get("created_at") or item.get("timestamp") or ""),
                )
            )
        return notifications

    def queueNotification(self, source: str, severity: str, category: str, title: str, message: str, device_id: str = "") -> dict[str, object]:
        """Request that the bridge queue an assistant notification."""

        payload = {
            "intent": "assistant.queueNotification",
            "confidence": 1.0,
            "arguments": {
                "source": source,
                "severity": severity,
                "category": category,
                "title": title,
                "message": message,
                "device_id": device_id,
            },
        }
        response = self.submitIntent(payload)
        if isinstance(response, dict):
            return response
        return {"status": "ok"}

    def _registerPending(self, message: AuraMessage):
        """Track a request until a matching response arrives."""

        request_id = message.requestId or message.messageId
        event = Event()
        with self.pendingLock:
            self.pendingRequests[request_id] = event
            self.pendingPayloads.pop(request_id, None)

    def _finalizePending(self, requestId: str, success: bool, response: dict[str, Any] | None = None, error: str = ""):
        """Release a request waiter and keep track of the last payload."""

        with self.pendingLock:
            event = self.pendingRequests.get(requestId)
            if event is None:
                return
            if response is not None:
                self.pendingPayloads[requestId] = response
            if error:
                self.pendingPayloads[requestId] = {"success": False, "error": error}
            if success or error:
                event.set()

    def _processTransportPayload(self, payload):
        """Normalize and route a transport payload."""

        for message in self._normalizeMessages(payload):
            self.router.route(message)

    def _normalizeMessages(self, payload) -> list[AuraMessage]:
        """Normalize transport return values into AuraMessage objects."""

        if payload is None:
            return []
        if isinstance(payload, AuraMessage):
            return [payload]
        if isinstance(payload, list):
            messages = []
            for item in payload:
                if isinstance(item, AuraMessage):
                    messages.append(item)
                elif isinstance(item, dict):
                    messages.append(AuraMessage.fromDict(item))
            return messages
        if isinstance(payload, dict):
            if "messages" in payload and isinstance(payload["messages"], list):
                return self._normalizeMessages(payload["messages"])
            if "message" in payload and isinstance(payload["message"], dict):
                return [AuraMessage.fromDict(payload["message"])]
            if "category" in payload:
                return [AuraMessage.fromDict(payload)]
        return []

    def _resolveBridgeConfig(self) -> BridgeConfig:
        """Read bridge config from Aura config or defaults."""

        def as_bool(value, default=False):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "on"}

        def as_int(value, default=0):
            if value is None or value == "":
                return default
            return int(value)

        def as_float(value, default=0.0):
            if value is None or value == "":
                return default
            return float(value)

        config = getattr(self.context, "config", None)
        bridge = getattr(self.context, "homeAutomationConfig", None)
        if bridge is not None and hasattr(bridge, "bridge"):
            return bridge.bridge
        if config is not None:
            return BridgeConfig(
                host=str(config.get("homeAutomationBridge.host", BridgeConfig().host)),
                port=as_int(config.get("homeAutomationBridge.port", BridgeConfig().port), BridgeConfig().port),
                use_ssl=as_bool(config.get("homeAutomationBridge.ssl", BridgeConfig().use_ssl), BridgeConfig().use_ssl),
                timeout_seconds=as_float(config.get("homeAutomationBridge.timeout", BridgeConfig().timeout_seconds), BridgeConfig().timeout_seconds),
                protocol_path=str(config.get("homeAutomationBridge.protocolPath", BridgeConfig().protocol_path)),
                inbox_path=str(config.get("homeAutomationBridge.inboxPath", BridgeConfig().inbox_path)),
                subscriptions_path=str(config.get("homeAutomationBridge.subscriptionsPath", BridgeConfig().subscriptions_path)),
                heartbeat_path=str(config.get("homeAutomationBridge.heartbeatPath", BridgeConfig().heartbeat_path)),
                session_id=str(config.get("homeAutomationBridge.sessionId", BridgeConfig().session_id)),
                interface_name=str(config.get("homeAutomationBridge.interface", BridgeConfig().interface_name)),
                heartbeat_seconds=as_float(config.get("homeAutomationBridge.heartbeatSeconds", BridgeConfig().heartbeat_seconds), BridgeConfig().heartbeat_seconds),
            )
        return BridgeConfig()

    def _configuredSessionId(self) -> str | None:
        """Return the configured session id when one is provided."""

        session_id = getattr(self.bridgeConfig, "session_id", "")
        if not session_id or str(session_id).strip().lower() == "auto":
            return None
        return str(session_id)

    def _buildBridgeState(self, snapshot: dict[str, Any]) -> BridgeState:
        """Convert cached bridge state into compatibility models."""

        devices: list[Device] = []
        lights: list[LightDevice] = []
        cameras: list[CameraDevice] = []

        source_devices = snapshot.get("devices", []) if isinstance(snapshot, dict) else []
        source_lights = snapshot.get("lights", []) if isinstance(snapshot, dict) else []
        source_cameras = snapshot.get("cameras", []) if isinstance(snapshot, dict) else []

        for item in source_devices if isinstance(source_devices, list) else []:
            if isinstance(item, dict):
                devices.append(self._parseDevice(item))
        for item in source_lights if isinstance(source_lights, list) else []:
            if isinstance(item, dict):
                light = self._parseLight(item)
                lights.append(light)
                devices.append(light)
        for item in source_cameras if isinstance(source_cameras, list) else []:
            if isinstance(item, dict):
                camera = self._parseCamera(item)
                cameras.append(camera)
                devices.append(camera)

        return BridgeState(
            connected=bool(snapshot.get("connected", False)),
            bridge_name=str(snapshot.get("bridgeName") or "Unavailable"),
            lights=lights,
            cameras=cameras,
            devices=devices,
            last_error=str(snapshot.get("lastError") or ""),
        )

    @staticmethod
    def _parseDevice(item: dict[str, Any]) -> Device:
        """Build a compatibility device model from protocol data."""

        return Device(
            device_id=str(item.get("device_id") or item.get("id") or ""),
            name=str(item.get("name") or "Unknown Device"),
            category=str(item.get("category") or item.get("device_type") or "device"),
            online=bool(item.get("online", True)),
            last_command=str(item.get("last_command") or item.get("lastCommand") or ""),
            metadata=dict(item.get("metadata") or {}),
        )

    @staticmethod
    def _parseLight(item: dict[str, Any]) -> LightDevice:
        """Build a compatibility light model from protocol data."""

        base = AuraBridgeClient._parseDevice(item)
        return LightDevice(
            device_id=base.device_id,
            name=base.name,
            category="light",
            online=base.online,
            last_command=base.last_command,
            metadata=base.metadata,
            is_on=bool(item.get("is_on", item.get("isOn", False))),
            brightness=int(item.get("brightness", 0)),
            light_type=str(item.get("light_type", item.get("type", ""))),
            max_brightness=int(item.get("max_brightness", item.get("maxBrightness", 100))),
            color_temperature_kelvin=int(item.get("color_temperature_kelvin", item.get("kelvin", 2700))),
            color=str(item.get("color", "white")),
        )

    @staticmethod
    def _parseCamera(item: dict[str, Any]) -> CameraDevice:
        """Build a compatibility camera model from protocol data."""

        base = AuraBridgeClient._parseDevice(item)
        return CameraDevice(
            device_id=base.device_id,
            name=base.name,
            category="camera",
            online=base.online,
            last_command=base.last_command,
            metadata=base.metadata,
            status=str(item.get("status", "Idle")),
            stream_url=str(item.get("stream_url", "")),
            snapshot_url=str(item.get("snapshot_url", "")),
            resolution=str(item.get("resolution", "")),
            is_streaming=bool(item.get("is_streaming", False)),
            snapshot_count=int(item.get("snapshot_count", 0)),
        )

    def _findLight(self, deviceId: str, errorMessage: str) -> LightDevice:
        """Return one cached light or raise a compatibility error."""

        light = next((item for item in self.getLights() if item.device_id == deviceId), None)
        if light is None:
            raise LookupError(errorMessage)
        return light

    def _findCamera(self, deviceId: str, errorMessage: str) -> CameraDevice:
        """Return one cached camera or raise a compatibility error."""

        camera = next((item for item in self.getCameras() if item.device_id == deviceId), None)
        if camera is None:
            raise LookupError(errorMessage)
        return camera

    def _getLogger(self, name: str):
        """Return a child logger when Aura logging is available."""

        if self.context and getattr(self.context, "logger", None):
            return self.context.logger.getChild(name)
        return None
