import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class BotLogger:
    """
    Centralized logging system for the Discord bot.
    Creates a new log file each time the bot starts.
    """

    _instance: Optional['BotLogger'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """Initialize the logging system with file and console handlers."""
        # Create logs directory if it doesn't exist
        log_dir = Path(__file__).resolve().parent.parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        # Create a unique log file for this bot session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"bot_{timestamp}.log"

        # Create logger
        self._logger = logging.getLogger("f1bot")
        self._logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        self._logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        simple_formatter = logging.Formatter(
            fmt='[%(asctime)s] [%(levelname)-8s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler - detailed logging
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)

        # Console handler - less verbose
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)

        # Add handlers
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

        self._logger.info("=" * 80)
        self._logger.info(f"F1 Fantasy Bot Logger Initialized")
        self._logger.info(f"Log file: {log_file}")
        self._logger.info("=" * 80)

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Optional name for the logger (typically module name)

        Returns:
            Logger instance
        """
        if name:
            return logging.getLogger(f"f1bot.{name}")
        return self._logger

    @staticmethod
    def log_command_invocation(command_name: str, user: str, user_id: int, guild_id: int, **kwargs):
        """
        Log when a command is invoked.

        Args:
            command_name: Name of the command
            user: Username who invoked the command
            user_id: Discord user ID
            guild_id: Discord guild ID
            **kwargs: Additional command parameters
        """
        logger = logging.getLogger("f1bot.commands")
        params_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else "No parameters"
        logger.info(
            f"Command invoked: /{command_name} | User: {user} (ID: {user_id}) | Guild: {guild_id} | Parameters: {params_str}"
        )

    @staticmethod
    def log_command_success(command_name: str, user: str, message: str = ""):
        """Log successful command completion."""
        logger = logging.getLogger("f1bot.commands")
        logger.info(f"Command succeeded: /{command_name} | User: {user} | {message}")

    @staticmethod
    def log_command_error(command_name: str, user: str, error: Exception):
        """Log command errors."""
        logger = logging.getLogger("f1bot.commands")
        logger.error(
            f"Command failed: /{command_name} | User: {user} | Error: {type(error).__name__}: {str(error)}",
            exc_info=True
        )

    @staticmethod
    def log_database_operation(operation: str, success: bool, details: str = ""):
        """Log database operations."""
        logger = logging.getLogger("f1bot.database")
        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"
        logger.log(level, f"Database {operation} - {status} | {details}")

    @staticmethod
    def log_service_operation(service: str, operation: str, details: str = ""):
        """Log service-level operations."""
        logger = logging.getLogger(f"f1bot.services.{service}")
        logger.info(f"{operation} | {details}")

    @staticmethod
    def log_event(event_name: str, details: str = ""):
        """Log Discord events."""
        logger = logging.getLogger("f1bot.events")
        logger.info(f"Event: {event_name} | {details}")


# Create singleton instance
bot_logger = BotLogger()


# Convenience functions
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance."""
    return bot_logger.get_logger(name)


def log_command(command_name: str, user: str, user_id: int, guild_id: int, **kwargs):
    """Log command invocation."""
    bot_logger.log_command_invocation(command_name, user, user_id, guild_id, **kwargs)


def log_success(command_name: str, user: str, message: str = ""):
    """Log command success."""
    bot_logger.log_command_success(command_name, user, message)


def log_error(command_name: str, user: str, error: Exception):
    """Log command error."""
    bot_logger.log_command_error(command_name, user, error)


def log_db(operation: str, success: bool, details: str = ""):
    """Log database operation."""
    bot_logger.log_database_operation(operation, success, details)


def log_service(service: str, operation: str, details: str = ""):
    """Log service operation."""
    bot_logger.log_service_operation(service, operation, details)


def log_event(event_name: str, details: str = ""):
    """Log Discord event."""
    bot_logger.log_event(event_name, details)