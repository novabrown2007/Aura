"""Core implementation for `configLoader` in the Aura assistant project."""

import yaml
from pathlib import Path


class ConfigLoader:
    """
    Loads and provides access to Aura configuration stored in YAML.

    The configuration file is loaded once at startup and stored in memory.
    Values can be accessed using dot-notation paths.

    Example:
        config.get("llm.model")
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
        self.data = {}

        self.load()

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def load(self):
        """
        Load configuration from the YAML file.
        """

        if not self.path.exists():
            raise FileNotFoundError(f"Config file not found: {self.path}")

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
                    "llm.model"

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
