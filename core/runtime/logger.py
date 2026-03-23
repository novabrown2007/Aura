import logging
import sys


class AuraLogger:
    """
    Central logging system for the Aura assistant.

    This class wraps Python's built-in logging module to provide a consistent
    logging interface across the entire application. It supports console logging,
    optional file logging, and hierarchical child loggers for modules.

    The logger is intended to be initialized once by the engine and then stored
    in the RuntimeContext so it can be accessed throughout the system.

    Example:
        context.logger = AuraLogger(level=logging.DEBUG)

        logger = context.logger.get_child("Engine")
        logger.info("Engine started")
    """

    def __init__(self, name="Aura", level=logging.INFO, log_to_file=False, file_path="aura.log"):
        """
        Initialize the Aura logging system.

        Args:
            name (str): Root logger name.
            level (int): Logging level (e.g., logging.INFO, logging.DEBUG).
            log_to_file (bool): Whether logs should also be written to a file.
            file_path (str): Path to the log file if file logging is enabled.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Prevent duplicate handlers if the logger is initialized multiple times
        if not self.logger.handlers:

            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )

            # Console output handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # Optional file logging
            if log_to_file:
                file_handler = logging.FileHandler(file_path)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

            if self.logger:
                self.logger.info(f"logger.py has been initialized.")

    def debug(self, message: str):
        """
        Log a debug message.

        Args:
            message (str): The debug message to log.
        """
        self.logger.debug(message)

    def info(self, message: str):
        """
        Log an informational message.

        Args:
            message (str): The informational message to log.
        """
        self.logger.info(message)

    def warning(self, message: str):
        """
        Log a warning message.

        Args:
            message (str): The warning message to log.
        """
        self.logger.warning(message)

    def error(self, message: str):
        """
        Log an error message.

        Args:
            message (str): The error message to log.
        """
        self.logger.error(message)

    def critical(self, message: str):
        """
        Log a critical error message.

        Args:
            message (str): The critical message to log.
        """
        self.logger.critical(message)

    def getChild(self, name: str):
        """
        Create a child logger for a subsystem or module.

        Child loggers inherit configuration from the root logger but include
        an additional name segment to identify the subsystem generating logs.

        Args:
            name (str): Name of the child logger.

        Returns:
            logging.Logger: A configured child logger instance.

        Example:
            logger = context.logger.get_child("Database")
            logger.info("Connected to database")
        """
        return self.logger.getChild(name)
