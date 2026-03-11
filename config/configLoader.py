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

    def __init__(self, context=None, path: str = "config/config.yml"):
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
            self.data = yaml.safe_load(file) or {}

        if self.logger:
            self.logger.info(f"Configuration loaded from {self.path}")

    # --------------------------------------------------
    # Access
    # --------------------------------------------------

    def get(self, key: str, default=None):
        """
        Retrieve a configuration value using dot notation.

        Args:
            key (str):
                Dot-separated configuration path.

                Example:
                    "llm.model"

            default:
                Value returned if the key does not exist.

        Returns:
            Any
        """
        parts = key.split(".")
        value = self.data

        for part in parts:
            if not isinstance(value, dict):
                return default
            value = value.get(part)
            if value is None:
                return default
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

    def as_dict(self):
        """
        Return the full configuration dictionary.
        """
        return self.data
