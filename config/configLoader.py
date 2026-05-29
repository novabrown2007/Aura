"""Core implementation for `configLoader` in the Aura assistant project."""

import os
import yaml
from pathlib import Path


DEFAULT_USER_CONFIG = {
    "llm": {
        "ollama": {
            "endpoint": "CHANGE_ME",
        },
        "gemini": {
            "api_secret": "CHANGE_ME",
        },
    },
    "huggingFace": {
        "apiToken": "CHANGE_ME",
    },
    "database": {
        "host": "localhost",
        "port": 3306,
        "name": "aura",
        "user": "CHANGE_ME",
        "password": "CHANGE_ME",
    },
    "voice": {
        "pushToTalk": {
            "enabled": True,
            "pushToTalkAutoSpeak": True,
        },
        "alwaysActive": {
            "enabled": True,
            "activationPhrases": ["Hey Jarvis"],
        },
    },
    "homeAutomationBridge": {
        "host": "127.0.0.1",
        "port": 8080,
        "ssl": False,
    },
    "modules": {
        "llm": "enabled",
        "calendar": "enabled",
        "database": "enabled",
        "home_automation": "enabled",
        "notifications": "enabled",
        "reminders": "enabled",
        "system": "enabled",
    },
}


DEFAULT_DEV_CONFIG = {
    "logging": {
        "logPath": "./logs/",
        "llmLogPath": "./logs/llm/",
        "loggingEnabled": True,
        "consoleLoggingEnabled": True,
        "fileLoggingEnabled": True,
        "debugLoggingEnabled": True,
    },
    "interruptions": {
        "interruptionsEnabled": True,
        "interruptionVoiceCommandsEnabled": True,
        "interruptionClearConversationState": True,
        "interruptionDebugLogging": True,
    },
    "llm": {
        "activeProvider": "ollama",
        "fallbackProvider": "gemini",
        "retryCount": 2,
        "timeout": 30,
        "ollama": {
            "model": "gemma4:e4b",
        },
        "gemini": {
            "model": "gemini-2.5-flash",
        },
        "history": {
            "enabled": True,
            "limit": 25,
            "persistAcrossRestarts": True,
        },
        "memory": {
            "enabled": True,
            "frequency": 5,
            "semantic": {
                "enabled": True,
                "limit": 6,
                "provider": "local",
            },
        },
        "logging": {
            "enabled": True,
            "path": "./logs/llm/",
        },
        "intent": {
            "confidenceThreshold": 0.75,
            "contextWindow": 6,
        },
    },
    "threading": {
        "max_threads": 10,
    },
    "voice": {
        "STT": {
            "enabled": True,
            "model": "small.en",
            "device": "cpu",
            "computeType": "int8",
            "sampleRate": 16000,
        },
        "TTS": {
            "voiceEnabled": True,
            "voiceModelPath": "en_US-lessac-medium",
            "voiceOutputDirectory": "temp/voice",
            "voicePlaybackEnabled": True,
            "voiceSampleRate": 22050,
            "voiceAutoDownloadModel": True,
        },
        "pushToTalk": {
            "pushToTalkHotkey": "enter",
            "pushToTalkAutoSpeak": True,
            "pushToTalkTempAudioDirectory": "temp/push_to_talk",
        },
        "alwaysActive": {
            "wakeWordSensitivity": 0.5,
            "wakeWordCooldownSeconds": 5,
            "wakeWordMicrophoneDevice": None,
            "wakeWordModelPath": "",
            "wakeWordInferenceFramework": "onnx",
            "wakeWordAutoStart": True,
            "wakeWordDebugLogging": False,
            "wakeWordDebugLoggingLocation": "logs/wake_word",
            "wakeWordResumeDelaySeconds": 1.5,
            "wakeWordAllowPretrainedFallback": True,
            "wakeWordFallbackModel": "hey_jarvis",
            "wakeWordAutoDownloadModels": True,
        },
    },
    "memory": {
        "enabled": True,
        "databasePath": "aura_memory.sqlite3",
        "maxResults": 10,
        "summaryLength": 280,
        "importanceThreshold": 0.35,
        "autoSummarization": True,
        "injectionEnabled": True,
        "maxInjectionCount": 10,
        "maxInjectionCharacters": 1024,
        "recencyWeight": 0.18,
        "importanceWeight": 0.24,
        "duplicateFiltering": True,
        "compressionEnabled": True,
        "minRelevance": 0.2,
        "retrievalCandidateLimit": 24,
        "retrievalDebug": True,
    },
    "developerUI": {
        "enabled": True,
        "refreshRate": 1000,
        "maxEvents": 500,
        "verboseLogging": False,
        "traceEvents": True,
    },
    "conversation": {
        "conversationTimeoutSeconds": 300,
    },
    "homeAutomationBridge": {
        "timeout": 5,
        "refreshSeconds": 5,
        "protocolPath": "/protocol/aura",
        "inboxPath": "/protocol/inbox",
        "subscriptionsPath": "/protocol/subscriptions",
        "heartbeatPath": "/protocol/heartbeat",
        "sessionId": "auto",
        "interface": "windows",
        "heartbeatSeconds": 30,
    },
}


CONFIG_ALIASES = {
    "voice.enabled": "voice.STT.enabled",
    "voice.model": "voice.STT.model",
    "voice.device": "voice.STT.device",
    "voice.computeType": "voice.STT.computeType",
    "voice.sampleRate": "voice.STT.sampleRate",
    "voice.voiceEnabled": "voice.TTS.voiceEnabled",
    "voice.voiceModelPath": "voice.TTS.voiceModelPath",
    "voice.voiceOutputDirectory": "voice.TTS.voiceOutputDirectory",
    "voice.voicePlaybackEnabled": "voice.TTS.voicePlaybackEnabled",
    "voice.voiceSampleRate": "voice.TTS.voiceSampleRate",
    "voice.pushToTalkEnabled": "voice.pushToTalk.enabled",
    "voice.PTT.pushToTalkEnabled": "voice.pushToTalk.enabled",
    "voice.pushToTalkHotkey": "voice.pushToTalk.pushToTalkHotkey",
    "voice.PTT.pushToTalkHotkey": "voice.pushToTalk.pushToTalkHotkey",
    "voice.pushToTalkAutoSpeak": "voice.pushToTalk.pushToTalkAutoSpeak",
    "voice.PTT.pushToTalkAutoSpeak": "voice.pushToTalk.pushToTalkAutoSpeak",
    "voice.pushToTalkTempAudioDirectory": "voice.pushToTalk.pushToTalkTempAudioDirectory",
    "voice.PTT.pushToTalkTempAudioDirectory": "voice.pushToTalk.pushToTalkTempAudioDirectory",
    "voice.alwaysActive.wakeWordEnabled": "voice.alwaysActive.enabled",
    "voice.alwaysActive.wakeWordPhrases": "voice.alwaysActive.activationPhrases",
    "voice.wakeWord.wakeWordEnabled": "voice.alwaysActive.enabled",
    "voice.wakeWord.wakeWordPhrase": "voice.alwaysActive.activationPhrase",
    "voice.wakeWord.wakeWordPhrases": "voice.alwaysActive.activationPhrases",
    "voice.wakeWord.wakeWordSensitivity": "voice.alwaysActive.wakeWordSensitivity",
    "voice.wakeWord.wakeWordCooldownSeconds": "voice.alwaysActive.wakeWordCooldownSeconds",
    "voice.wakeWord.wakeWordMicrophoneDevice": "voice.alwaysActive.wakeWordMicrophoneDevice",
    "voice.wakeWord.wakeWordModelPath": "voice.alwaysActive.wakeWordModelPath",
    "voice.wakeWord.wakeWordInferenceFramework": "voice.alwaysActive.wakeWordInferenceFramework",
    "voice.wakeWord.wakeWordAutoStart": "voice.alwaysActive.wakeWordAutoStart",
    "voice.wakeWord.wakeWordDebugLogging": "voice.alwaysActive.wakeWordDebugLogging",
    "voice.wakeWord.wakeWordDebugLoggingLocation": "voice.alwaysActive.wakeWordDebugLoggingLocation",
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Return a recursive merge where override values win."""

    merged = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


DEFAULT_CONFIG = _deep_merge(DEFAULT_DEV_CONFIG, DEFAULT_USER_CONFIG)


class ConfigLoader:
    """
    Loads and provides access to Aura configuration stored in YAML.

    The configuration file is loaded once at startup and stored in memory.
    Values can be accessed using dot-notation paths.

    Example:
        config.get("llm.ollama.model")
        config.get("llm.history.limit")
    """

    def __init__(self, context=None, path: str | Path | None = None, devPath: str | Path | None = None):
        """
        Initialize the configuration loader.

        Args:
            context (RuntimeContext | None):
                Optional runtime context for logging.

            path (str | Path | None):
                Path to the user-facing configuration file. When omitted,
                Aura loads the package-local `config/config.yml`.

            devPath (str | Path | None):
                Path to backend/developer configuration. When omitted, Aura
                loads the package-local `config/devConfig.yml`.
        """

        self.context = context
        self.logger = None

        if context and context.logger:
            self.logger = context.logger.getChild("Config")

        config_dir = Path(__file__).resolve().parent
        self.path = Path(path) if path is not None else config_dir / "config.yml"
        self.devPath = Path(devPath) if devPath is not None else config_dir / "devConfig.yml"
        self.env_path = Path(".env")
        self.data = {}
        self.userData = {}
        self.devData = {}
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
            "huggingFace.apiToken": "HF_TOKEN",
            "huggingFace.token": "HF_TOKEN",
            "huggingface.apiToken": "HF_TOKEN",
            "huggingface.token": "HF_TOKEN",
            "discord.webhook": "DISCORD_WEBHOOK_URL",
            "discord.webhook_url": "DISCORD_WEBHOOK_URL",
            "discord.webhookUrl": "DISCORD_WEBHOOK_URL",
            "voice.enabled": "VOICE_INPUT_ENABLED",
            "voice.STT.enabled": "VOICE_INPUT_ENABLED",
            "voiceEnabled": "VOICE_ENABLED",
            "voice.model": "VOICE_INPUT_MODEL",
            "voice.STT.model": "VOICE_INPUT_MODEL",
            "voiceModel": "VOICE_INPUT_MODEL",
            "voice.device": "VOICE_INPUT_DEVICE",
            "voice.STT.device": "VOICE_INPUT_DEVICE",
            "voiceDevice": "VOICE_INPUT_DEVICE",
            "voice.computeType": "VOICE_INPUT_COMPUTE_TYPE",
            "voice.STT.computeType": "VOICE_INPUT_COMPUTE_TYPE",
            "voiceComputeType": "VOICE_INPUT_COMPUTE_TYPE",
            "voice.sampleRate": "VOICE_INPUT_SAMPLE_RATE",
            "voice.STT.sampleRate": "VOICE_INPUT_SAMPLE_RATE",
            "voiceSampleRate": "VOICE_SAMPLE_RATE",
            "voice.voiceEnabled": "VOICE_ENABLED",
            "voice.TTS.voiceEnabled": "VOICE_ENABLED",
            "voice.voiceModelPath": "VOICE_MODEL_PATH",
            "voice.TTS.voiceModelPath": "VOICE_MODEL_PATH",
            "voice.voiceOutputDirectory": "VOICE_OUTPUT_DIRECTORY",
            "voice.TTS.voiceOutputDirectory": "VOICE_OUTPUT_DIRECTORY",
            "voice.voicePlaybackEnabled": "VOICE_PLAYBACK_ENABLED",
            "voice.TTS.voicePlaybackEnabled": "VOICE_PLAYBACK_ENABLED",
            "voice.voiceSampleRate": "VOICE_SAMPLE_RATE",
            "voice.TTS.voiceSampleRate": "VOICE_SAMPLE_RATE",
            "voice.modelPath": "VOICE_MODEL_PATH",
            "voice.outputDirectory": "VOICE_OUTPUT_DIRECTORY",
            "voice.playbackEnabled": "VOICE_PLAYBACK_ENABLED",
            "voice.pushToTalk.enabled": "PUSH_TO_TALK_ENABLED",
            "voice.pushToTalkEnabled": "PUSH_TO_TALK_ENABLED",
            "voice.pushToTalkHotkey": "PUSH_TO_TALK_HOTKEY",
            "voice.pushToTalk.pushToTalkHotkey": "PUSH_TO_TALK_HOTKEY",
            "voice.pushToTalkAutoSpeak": "PUSH_TO_TALK_AUTO_SPEAK",
            "voice.pushToTalk.pushToTalkAutoSpeak": "PUSH_TO_TALK_AUTO_SPEAK",
            "voice.pushToTalkTempAudioDirectory": "PUSH_TO_TALK_TEMP_AUDIO_DIRECTORY",
            "voice.pushToTalk.pushToTalkTempAudioDirectory": "PUSH_TO_TALK_TEMP_AUDIO_DIRECTORY",
            "voice.alwaysActive.enabled": "WAKE_WORD_ENABLED",
            "voice.alwaysActive.activationPhrase": "WAKE_WORD_PHRASE",
            "voice.alwaysActive.activationPhrases": "WAKE_WORD_PHRASES",
            "voice.alwaysActive.wakeWordPhrase": "WAKE_WORD_PHRASE",
            "voice.alwaysActive.wakeWordPhrases": "WAKE_WORD_PHRASES",
            "voice.alwaysActive.wakeWordSensitivity": "WAKE_WORD_SENSITIVITY",
            "voice.alwaysActive.wakeWordCooldownSeconds": "WAKE_WORD_COOLDOWN_SECONDS",
            "voice.alwaysActive.wakeWordMicrophoneDevice": "WAKE_WORD_MICROPHONE_DEVICE",
            "voice.alwaysActive.wakeWordModelPath": "WAKE_WORD_MODEL_PATH",
            "voice.alwaysActive.wakeWordInferenceFramework": "WAKE_WORD_INFERENCE_FRAMEWORK",
            "voice.alwaysActive.wakeWordAutoStart": "WAKE_WORD_AUTO_START",
            "voice.alwaysActive.wakeWordDebugLogging": "WAKE_WORD_DEBUG_LOGGING",
            "voice.alwaysActive.wakeWordDebugLoggingLocation": "WAKE_WORD_DEBUG_LOGGING_LOCATION",
            "wakeWordPhrase": "WAKE_WORD_PHRASE",
            "wakeWordPhrases": "WAKE_WORD_PHRASES",
            "activationPhrase": "WAKE_WORD_PHRASE",
            "activationPhrases": "WAKE_WORD_PHRASES",
            "wakeWordSensitivity": "WAKE_WORD_SENSITIVITY",
            "wakeWordCooldownSeconds": "WAKE_WORD_COOLDOWN_SECONDS",
            "wakeWordMicrophoneDevice": "WAKE_WORD_MICROPHONE_DEVICE",
            "wakeWordModelPath": "WAKE_WORD_MODEL_PATH",
            "wakeWordInferenceFramework": "WAKE_WORD_INFERENCE_FRAMEWORK",
            "wakeWordAutoStart": "WAKE_WORD_AUTO_START",
            "wakeWordDebugLogging": "WAKE_WORD_DEBUG_LOGGING",
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

        if not self.devPath.exists():
            self._createDefaultConfig(self.devPath, DEFAULT_DEV_CONFIG, "developer")

        if not self.path.exists():
            self._createDefaultConfig(self.path, DEFAULT_USER_CONFIG, "user")

        self.devData = self._loadYamlFile(self.devPath)
        self.userData = self._loadYamlFile(self.path)
        self.data = _deep_merge(self.devData, self.userData)

        # --------------------------------------------------
        # Logging
        # --------------------------------------------------

        if self.logger:
            self.logger.info(f"Configuration loaded from {self.path} and {self.devPath}")
            keys = ", ".join(self.data.keys())
            self.logger.debug(f"Config sections loaded: {keys}")

    def _createDefaultConfig(self, path: Path, defaults: dict, label: str):
        """
        Create a default configuration file when Aura starts without one.
        """

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            yaml.safe_dump(defaults, file, sort_keys=False)

        if self.logger:
            self.logger.warning(f"{label.title()} config file missing. Created default config at {path}")

    def _loadYamlFile(self, path: Path) -> dict:
        """Load one YAML config file and validate its root shape."""

        with open(path, "r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file)

        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config root must be a dictionary: {path}")
        return loaded

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

        value = self._getRaw(key, None)
        if value is None and key in CONFIG_ALIASES:
            value = self._getRaw(CONFIG_ALIASES[key], None)
        if value is None:
            return default
        if self._isPlaceholder(value):
            return self._getEnvFallback(key, default)
        return value

    def _getRaw(self, key: str, default=None):
        """Retrieve a raw config value without alias or environment handling."""

        value = self.data
        for part in key.split("."):
            if not isinstance(value, dict):
                return default
            if part not in value:
                return default
            value = value[part]
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

    @staticmethod
    def _isPlaceholder(value) -> bool:
        """Return true when a config value intentionally delegates to .env."""

        return isinstance(value, str) and value.strip().lower() == "change_me"
