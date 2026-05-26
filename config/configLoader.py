"""Core implementation for `configLoader` in the Aura assistant project."""

import os
import yaml
from pathlib import Path


DEFAULT_CONFIG = {
    "llm": {
        "activeProvider": "gemini",
        "fallbackProvider": "ollama",
        "retryCount": 2,
        "timeout": 30,
        "ollama": {
            "model": "llama3.2:1b",
            "endpoint": "CHANGE_ME",
        },
        "gemini": {
            "model": "gemini-2.5-flash",
            "api_secret": "CHANGE_ME",
        },
        "history": {
            "enabled": True,
            "limit": 25,
            "persistAcrossRestarts": False,
        },
        "memory": {
            "enabled": True,
            "frequency": 20,
            "semantic": {
                "enabled": True,
                "limit": 5,
                "provider": "local",
            },
        },
        "logging": {
            "enabled": True,
            "path": "logs/llm",
        },
        "intent": {
            "confidenceThreshold": 0.75,
            "contextWindow": 6,
        },
    },
    "database": {
        "host": "localhost",
        "port": 3306,
        "name": "aura",
        "user": "CHANGE_ME",
        "password": "CHANGE_ME",
    },
    "threading": {
        "max_threads": 10,
    },
    "voice": {
        "enabled": False,
        "model": "small.en",
        "device": "cpu",
        "computeType": "int8",
        "sampleRate": 16000,
        "voiceEnabled": True,
        "voiceModelPath": "en_US-lessac-medium.onnx",
        "voiceOutputDirectory": "temp/voice",
        "voicePlaybackEnabled": True,
        "voiceSampleRate": 22050,
        "pushToTalkEnabled": False,
        "pushToTalkHotkey": "enter",
        "pushToTalkAutoSpeak": True,
        "pushToTalkTempAudioDirectory": "temp/push_to_talk",
    },
    "pushToTalkEnabled": False,
    "pushToTalkHotkey": "enter",
    "pushToTalkAutoSpeak": True,
    "pushToTalkTempAudioDirectory": "temp/push_to_talk",
    "memory": {
        "enabled": True,
        "databasePath": "aura_memory.sqlite3",
        "maxResults": 8,
        "summaryLength": 280,
        "importanceThreshold": 0.35,
        "autoSummarization": True,
        "injectionEnabled": True,
        "maxInjectionCount": 5,
        "maxInjectionCharacters": 900,
        "recencyWeight": 0.18,
        "importanceWeight": 0.24,
        "duplicateFiltering": True,
        "compressionEnabled": True,
        "minRelevance": 0.18,
        "retrievalCandidateLimit": 24,
        "retrievalDebug": True,
    },
    "memoryEnabled": True,
    "memoryDatabasePath": "aura_memory.sqlite3",
    "memoryMaxResults": 8,
    "memorySummaryLength": 280,
    "memoryImportanceThreshold": 0.35,
    "memoryAutoSummarization": True,
    "memoryInjectionEnabled": True,
    "memoryMaxInjectionCount": 5,
    "memoryMaxInjectionCharacters": 900,
    "memoryRecencyWeight": 0.18,
    "memoryImportanceWeight": 0.24,
    "memoryDuplicateFiltering": True,
    "memoryCompressionEnabled": True,
    "developerUI": {
        "enabled": True,
        "refreshRate": 750,
        "maxEvents": 500,
        "verboseLogging": False,
        "traceEvents": True,
    },
    "developerUIEnabled": True,
    "developerUIRefreshRate": 750,
    "developerUIMaxEvents": 500,
    "developerUIVerboseLogging": False,
    "developerUITraceEvents": True,
    "homeAutomationBridge": {
        "host": "127.0.0.1",
        "port": 8080,
        "ssl": False,
        "timeout": 5,
        "refreshSeconds": 5,
        "protocolPath": "/protocol/aura",
        "inboxPath": "/protocol/inbox",
        "subscriptionsPath": "/protocol/subscriptions",
        "heartbeatPath": "/protocol/heartbeat",
        "sessionId": "auto",
        "interface": "desktop",
        "heartbeatSeconds": 30,
    },
}


class ConfigLoader:
    """
    Loads and provides access to Aura configuration stored in YAML.

    The configuration file is loaded once at startup and stored in memory.
    Values can be accessed using dot-notation paths.

    Example:
        config.get("llm.ollama.model")
        config.get("llm.history.limit")
    """

    def __init__(self, context=None, path: str = "config.yml"):
        """
        Initialize the configuration loader.

        Args:
            context (RuntimeContext | None):
                Optional runtime context for logging.

            path (str):
                Path to the configuration file.
        """

        self.context = context
        self.logger = None

        if context and context.logger:
            self.logger = context.logger.getChild("Config")

        self.path = Path(path)
        self.env_path = Path(".env")
        self.data = {}
        self.env_key_map = {
            "llm.endpoint": "OLLAMA_ENDPOINT",
            "llm.ollama.endpoint": "OLLAMA_ENDPOINT",
            "llm.providers.ollama.endpoint": "OLLAMA_ENDPOINT",
            "llm.model": "OLLAMA_MODEL",
            "llm.ollama.model": "OLLAMA_MODEL",
            "llm.providers.ollama.model": "OLLAMA_MODEL",
            "llm.gemini.api_secret": "GEMINI_API_KEY",
            "llm.gemini.apiKey": "GEMINI_API_KEY",
            "llm.providers.gemini.apiKey": "GEMINI_API_KEY",
            "llm.providers.gemini.api_secret": "GEMINI_API_KEY",
            "discord.webhook": "DISCORD_WEBHOOK_URL",
            "discord.webhook_url": "DISCORD_WEBHOOK_URL",
            "discord.webhookUrl": "DISCORD_WEBHOOK_URL",
            "voice.enabled": "VOICE_INPUT_ENABLED",
            "voiceEnabled": "VOICE_ENABLED",
            "voice.model": "VOICE_INPUT_MODEL",
            "voiceModel": "VOICE_INPUT_MODEL",
            "voice.device": "VOICE_INPUT_DEVICE",
            "voiceDevice": "VOICE_INPUT_DEVICE",
            "voice.computeType": "VOICE_INPUT_COMPUTE_TYPE",
            "voiceComputeType": "VOICE_INPUT_COMPUTE_TYPE",
            "voice.sampleRate": "VOICE_INPUT_SAMPLE_RATE",
            "voiceSampleRate": "VOICE_SAMPLE_RATE",
            "voice.voiceEnabled": "VOICE_ENABLED",
            "voice.voiceModelPath": "VOICE_MODEL_PATH",
            "voice.voiceOutputDirectory": "VOICE_OUTPUT_DIRECTORY",
            "voice.voicePlaybackEnabled": "VOICE_PLAYBACK_ENABLED",
            "voice.voiceSampleRate": "VOICE_SAMPLE_RATE",
            "voice.modelPath": "VOICE_MODEL_PATH",
            "voice.outputDirectory": "VOICE_OUTPUT_DIRECTORY",
            "voice.playbackEnabled": "VOICE_PLAYBACK_ENABLED",
            "voice.pushToTalkEnabled": "PUSH_TO_TALK_ENABLED",
            "voice.pushToTalkHotkey": "PUSH_TO_TALK_HOTKEY",
            "voice.pushToTalkAutoSpeak": "PUSH_TO_TALK_AUTO_SPEAK",
            "voice.pushToTalkTempAudioDirectory": "PUSH_TO_TALK_TEMP_AUDIO_DIRECTORY",
            "pushToTalkEnabled": "PUSH_TO_TALK_ENABLED",
            "pushToTalkHotkey": "PUSH_TO_TALK_HOTKEY",
            "pushToTalkAutoSpeak": "PUSH_TO_TALK_AUTO_SPEAK",
            "pushToTalkTempAudioDirectory": "PUSH_TO_TALK_TEMP_AUDIO_DIRECTORY",
            "developerUI.enabled": "DEVELOPER_UI_ENABLED",
            "developerUI.refreshRate": "DEVELOPER_UI_REFRESH_RATE",
            "developerUI.maxEvents": "DEVELOPER_UI_MAX_EVENTS",
            "developerUI.verboseLogging": "DEVELOPER_UI_VERBOSE_LOGGING",
            "developerUI.traceEvents": "DEVELOPER_UI_TRACE_EVENTS",
            "developerUIEnabled": "DEVELOPER_UI_ENABLED",
            "developerUIRefreshRate": "DEVELOPER_UI_REFRESH_RATE",
            "developerUIMaxEvents": "DEVELOPER_UI_MAX_EVENTS",
            "developerUIVerboseLogging": "DEVELOPER_UI_VERBOSE_LOGGING",
            "developerUITraceEvents": "DEVELOPER_UI_TRACE_EVENTS",
        }

        self.load()

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def load(self):
        """
        Load configuration from the YAML file.
        """

        self._loadEnvFile()

        if not self.path.exists():
            self._createDefaultConfig()

        with open(self.path, "r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file)

        if not isinstance(loaded, dict):
            raise ValueError(f"Config root must be a dictionary: {self.path}")

        self.data = loaded

        # --------------------------------------------------
        # Logging
        # --------------------------------------------------

        if self.logger:
            self.logger.info(f"Configuration loaded from {self.path}")
            keys = ", ".join(self.data.keys())
            self.logger.debug(f"Config sections loaded: {keys}")

    def _createDefaultConfig(self):
        """
        Create a default configuration file when Aura starts without one.
        """

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            yaml.safe_dump(DEFAULT_CONFIG, file, sort_keys=False)

        if self.logger:
            self.logger.warning(f"Config file missing. Created default config at {self.path}")

    # --------------------------------------------------
    # Access
    # --------------------------------------------------

    def get(self, key: str, default=None):
        """
        Retrieve a configuration value using dot notation.

        Args:
            :param key: (str):
                Dot-separated configuration path.

                Example:
                    "llm.ollama.model"

            :param default:
                Value returned if the key does not exist.

        Returns:
            Any
        """

        value = self.data
        for part in key.split("."):
            if not isinstance(value, dict):
                return default
            if part not in value:
                return default
            value = value[part]
        if value == "CHANGE_ME":
            return self._getEnvFallback(key, default)
        return value

    def require(self, key: str):
        """
        Retrieve a required configuration value.

        Raises an error if the value does not exist.

        Args:
            key (str):
                Dot-separated configuration path.

        Returns:
            Any

        Raises:
            KeyError:
                If the configuration value is missing.
        """

        value = self.get(key)

        if value is None:
            raise KeyError(f"Missing required config value: {key}")

        return value


    # --------------------------------------------------
    # Utility
    # --------------------------------------------------

    def reload(self):
        """
        Reload the configuration file.
        """

        self.load()

        if self.logger:
            self.logger.info("Configuration reloaded")

    def asDict(self):
        """
        Return the full configuration dictionary.
        """
        return self.data

    def _loadEnvFile(self):
        """
        Load local .env values into os.environ without external dependencies.

        Existing environment variables win over .env values so CI and shell
        overrides remain authoritative.
        """

        if not self.env_path.exists():
            return

        with open(self.env_path, "r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value

    def _getEnvFallback(self, key: str, default=None):
        """
        Return an environment value for config entries intentionally marked CHANGE_ME.
        """

        env_key = self.env_key_map.get(key)
        if not env_key:
            return default
        env_value = os.getenv(env_key)
        if env_value in (None, ""):
            return default
        return env_value
