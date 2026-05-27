"""Tests for Aura configuration loading behavior."""

import os
import tempfile
import unittest
from pathlib import Path

from config.configLoader import ConfigLoader


class ConfigLoaderTests(unittest.TestCase):
    """Validate config placeholder and environment fallback behavior."""

    def test_change_me_uses_mapped_environment_variable(self):
        """CHANGE_ME values should resolve through their mapped .env variable."""

        old_value = os.environ.get("OLLAMA_ENDPOINT")
        os.environ["OLLAMA_ENDPOINT"] = "http://env-ollama/api/generate"

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "config.yml"
                config_path.write_text(
                    "llm:\n"
                    "  ollama:\n"
                    "    endpoint: CHANGE_ME\n",
                    encoding="utf-8",
                )

                config = ConfigLoader(path=str(config_path))

                self.assertEqual(
                    config.get("llm.ollama.endpoint"),
                    "http://env-ollama/api/generate",
                )
        finally:
            if old_value is None:
                os.environ.pop("OLLAMA_ENDPOINT", None)
            else:
                os.environ["OLLAMA_ENDPOINT"] = old_value

    def test_ollama_model_can_use_environment_fallback(self):
        """Ollama model placeholders should resolve through OLLAMA_MODEL."""

        old_value = os.environ.get("OLLAMA_MODEL")
        os.environ["OLLAMA_MODEL"] = "llama3.2:1b"

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "config.yml"
                config_path.write_text(
                    "llm:\n"
                    "  ollama:\n"
                    "    model: CHANGE_ME\n",
                    encoding="utf-8",
                )

                config = ConfigLoader(path=str(config_path))

                self.assertEqual(config.get("llm.ollama.model"), "llama3.2:1b")
        finally:
            if old_value is None:
                os.environ.pop("OLLAMA_MODEL", None)
            else:
                os.environ["OLLAMA_MODEL"] = old_value

    def test_literal_config_value_wins_over_environment_variable(self):
        """Only CHANGE_ME placeholders should use environment fallback values."""

        old_value = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "env-secret"

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "config.yml"
                config_path.write_text(
                    "llm:\n"
                    "  gemini:\n"
                    "    api_secret: config-secret\n",
                    encoding="utf-8",
                )

                config = ConfigLoader(path=str(config_path))

                self.assertEqual(config.get("llm.gemini.api_secret"), "config-secret")
        finally:
            if old_value is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = old_value

    def test_env_file_is_loaded_without_overwriting_existing_environment(self):
        """Local .env values should load only when the shell has not set them."""

        old_discord_value = os.environ.get("DISCORD_WEBHOOK_URL")
        old_cwd = os.getcwd()
        os.environ.pop("DISCORD_WEBHOOK_URL", None)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                (temp_path / ".env").write_text(
                    "DISCORD_WEBHOOK_URL=https://discord.test/webhook\n",
                    encoding="utf-8",
                )
                config_path = temp_path / "config.yml"
                config_path.write_text(
                    "discord:\n"
                    "  webhook_url: CHANGE_ME\n",
                    encoding="utf-8",
                )

                os.chdir(temp_path)
                config = ConfigLoader(path=str(config_path))

                self.assertEqual(
                    config.get("discord.webhook_url"),
                    "https://discord.test/webhook",
                )
                os.chdir(old_cwd)
        finally:
            os.chdir(old_cwd)
            if old_discord_value is None:
                os.environ.pop("DISCORD_WEBHOOK_URL", None)
            else:
                os.environ["DISCORD_WEBHOOK_URL"] = old_discord_value

    def test_missing_config_file_is_created_with_defaults(self):
        """Aura should create a default config file instead of crashing."""

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            dev_config_path = Path(temp_dir) / "devConfig.yml"

            config = ConfigLoader(path=str(config_path), devPath=str(dev_config_path))

            self.assertTrue(config_path.exists())
            self.assertEqual(config.get("llm.activeProvider"), "gemini")
            self.assertEqual(config.get("llm.ollama.model"), "llama3.2:1b")
            self.assertEqual(config.get("llm.history.persistAcrossRestarts"), True)
            self.assertEqual(config.asDict()["llm"]["ollama"]["endpoint"], "CHANGE_ME")
            self.assertEqual(config.get("threading.max_threads"), 10)
            self.assertEqual(config.get("voice.enabled"), False)
            self.assertEqual(config.get("voice.STT.enabled"), False)
            self.assertEqual(config.get("voice.model"), "small.en")
            self.assertEqual(config.get("voice.STT.model"), "small.en")
            self.assertEqual(config.get("voice.device"), "cpu")
            self.assertEqual(config.get("voice.computeType"), "int8")
            self.assertEqual(config.get("voice.sampleRate"), 16000)
            self.assertEqual(config.get("voice.voiceEnabled"), True)
            self.assertEqual(config.get("voice.TTS.voiceEnabled"), True)
            self.assertEqual(config.get("voice.voiceModelPath"), "en_US-lessac-medium")
            self.assertEqual(config.get("voice.voiceOutputDirectory"), "temp/voice")
            self.assertEqual(config.get("voice.voicePlaybackEnabled"), True)
            self.assertEqual(config.get("voice.voiceSampleRate"), 22050)
            self.assertEqual(config.get("voice.wakeWord.wakeWordDebugLoggingLocation"), "logs/wake_word")
            self.assertEqual(config.get("memory.maxResults"), 10)
            self.assertEqual(config.get("memory.maxInjectionCount"), 10)
            self.assertEqual(config.get("developerUI.refreshRate"), 1000)
            self.assertEqual(config.get("homeAutomationBridge.interface"), "windows")
            self.assertEqual(config.asDict()["homeAutomationBridge"]["host"], "127.0.0.1")
            self.assertEqual(config.asDict()["homeAutomationBridge"]["protocolPath"], "/protocol/aura")
            self.assertEqual(config.asDict()["homeAutomationBridge"]["sessionId"], "auto")

    def test_default_config_does_not_duplicate_nested_runtime_sections(self):
        """Nested runtime config should not be repeated as flat top-level keys."""

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yml"
            config = ConfigLoader(path=str(config_path))

            duplicate_keys = {
                "pushToTalkEnabled",
                "pushToTalkHotkey",
                "pushToTalkAutoSpeak",
                "pushToTalkTempAudioDirectory",
                "wakeWordEnabled",
                "wakeWordPhrase",
                "wakeWordPhrases",
                "wakeWordSensitivity",
                "wakeWordCooldownSeconds",
                "wakeWordMicrophoneDevice",
                "wakeWordModelPath",
                "wakeWordInferenceFramework",
                "wakeWordAutoStart",
                "wakeWordDebugLogging",
                "memoryEnabled",
                "memoryDatabasePath",
                "memoryMaxResults",
                "memorySummaryLength",
                "memoryImportanceThreshold",
                "memoryAutoSummarization",
                "memoryInjectionEnabled",
                "memoryMaxInjectionCount",
                "memoryMaxInjectionCharacters",
                "memoryRecencyWeight",
                "memoryImportanceWeight",
                "memoryDuplicateFiltering",
                "memoryCompressionEnabled",
                "developerUIEnabled",
                "developerUIRefreshRate",
                "developerUIMaxEvents",
                "developerUIVerboseLogging",
                "developerUITraceEvents",
            }

            self.assertFalse(duplicate_keys.intersection(config.asDict()))

    def test_default_config_path_is_package_local(self):
        """The runtime default config lives beside configLoader in the config package."""

        config = ConfigLoader()

        self.assertEqual(config.path, Path(__file__).resolve().parents[2] / "config" / "config.yml")
        self.assertEqual(config.devPath, Path(__file__).resolve().parents[2] / "config" / "devConfig.yml")

    def test_user_config_overrides_dev_config_after_merge(self):
        """User-facing config should override developer defaults at the same path."""

        with tempfile.TemporaryDirectory() as temp_dir:
            user_path = Path(temp_dir) / "config.yml"
            dev_path = Path(temp_dir) / "devConfig.yml"
            user_path.write_text(
                "llm:\n"
                "  activeProvider: ollama\n"
                "  gemini:\n"
                "    api_secret: user-secret\n",
                encoding="utf-8",
            )
            dev_path.write_text(
                "llm:\n"
                "  activeProvider: gemini\n"
                "  gemini:\n"
                "    model: gemini-2.5-flash\n",
                encoding="utf-8",
            )

            config = ConfigLoader(path=user_path, devPath=dev_path)

            self.assertEqual(config.get("llm.activeProvider"), "ollama")
            self.assertEqual(config.get("llm.gemini.api_secret"), "user-secret")
            self.assertEqual(config.get("llm.gemini.model"), "gemini-2.5-flash")

    def test_grouped_voice_dev_config_supports_legacy_voice_paths(self):
        """Runtime callers can keep reading old voice paths after config regrouping."""

        with tempfile.TemporaryDirectory() as temp_dir:
            user_path = Path(temp_dir) / "config.yml"
            dev_path = Path(temp_dir) / "devConfig.yml"
            user_path.write_text("llm: {}\n", encoding="utf-8")
            dev_path.write_text(
                "voice:\n"
                "  STT:\n"
                "    enabled: true\n"
                "    model: base.en\n"
                "    device: cuda\n"
                "    computeType: float16\n"
                "    sampleRate: 16000\n"
                "  TTS:\n"
                "    voiceEnabled: false\n"
                "    voiceModelPath: voice.onnx\n"
                "    voiceOutputDirectory: tmp/tts\n"
                "    voicePlaybackEnabled: false\n"
                "    voiceSampleRate: 24000\n"
                "  PTT:\n"
                "    pushToTalkEnabled: true\n"
                "    pushToTalkHotkey: space\n"
                "    pushToTalkAutoSpeak: false\n"
                "    pushToTalkTempAudioDirectory: tmp/ptt\n",
                encoding="utf-8",
            )

            config = ConfigLoader(path=user_path, devPath=dev_path)

            self.assertEqual(config.get("voice.enabled"), True)
            self.assertEqual(config.get("voice.model"), "base.en")
            self.assertEqual(config.get("voice.device"), "cuda")
            self.assertEqual(config.get("voice.computeType"), "float16")
            self.assertEqual(config.get("voice.voiceEnabled"), False)
            self.assertEqual(config.get("voice.voiceModelPath"), "voice.onnx")
            self.assertEqual(config.get("voice.pushToTalkEnabled"), True)
            self.assertEqual(config.get("voice.pushToTalkHotkey"), "space")

    def test_missing_config_files_are_created_separately(self):
        """User and developer config files should be generated independently."""

        with tempfile.TemporaryDirectory() as temp_dir:
            user_path = Path(temp_dir) / "config.yml"
            dev_path = Path(temp_dir) / "devConfig.yml"

            config = ConfigLoader(path=user_path, devPath=dev_path)

            self.assertTrue(user_path.exists())
            self.assertTrue(dev_path.exists())
            self.assertIn("database", config.userData)
            self.assertIn("developerUI", config.devData)


if __name__ == "__main__":
    unittest.main()
