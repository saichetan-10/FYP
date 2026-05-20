"""Simple logging configuration."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Try to import structlog, fall back to simple logging
USE_STRUCTLOG = False  # Disable structlog for now

from src.config import config


def configure_logging() -> None:
    """Configure logging."""
    # Create logs directory if it doesn't exist
    Path(config.logging.log_dir).mkdir(parents=True, exist_ok=True)


def get_logger(name: str):
    """Get a configured logger instance."""
    import logging
    return logging.getLogger(name)


class StructuredLogger:
    """Wrapper for structured logging with file persistence."""

    def __init__(self, name: str):
        """Initialize logger."""
        self.name = name
        self.logger = get_logger(name)
        self.log_file = Path(config.logging.log_path)

    def _write_to_file(self, level: str, event: str, **kwargs) -> None:
        """Write structured log to file."""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "logger": self.name,
                "event": event,
                **kwargs,
            }
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")

    def info(self, event: str, **kwargs) -> None:
        """Log info level."""
        if USE_STRUCTLOG:
            self.logger.info(event, **kwargs)
        else:
            print(f"INFO [{self.name}] {event}: {kwargs}")
        self._write_to_file("INFO", event, **kwargs)

    def error(self, event: str, **kwargs) -> None:
        """Log error level."""
        if USE_STRUCTLOG:
            self.logger.error(event, **kwargs)
        else:
            print(f"ERROR [{self.name}] {event}: {kwargs}")
        self._write_to_file("ERROR", event, **kwargs)

    def debug(self, event: str, **kwargs) -> None:
        """Log debug level."""
        if USE_STRUCTLOG:
            self.logger.debug(event, **kwargs)
        else:
            if config.debug:
                print(f"DEBUG [{self.name}] {event}: {kwargs}")
        if config.debug:
            self._write_to_file("DEBUG", event, **kwargs)

    def warning(self, event: str, **kwargs) -> None:
        """Log warning level."""
        if USE_STRUCTLOG:
            self.logger.warning(event, **kwargs)
        else:
            print(f"WARNING [{self.name}] {event}: {kwargs}")
        self._write_to_file("WARNING", event, **kwargs)

    def critical(self, event: str, **kwargs) -> None:
        """Log critical level."""
        if USE_STRUCTLOG:
            self.logger.critical(event, **kwargs)
        else:
            print(f"CRITICAL [{self.name}] {event}: {kwargs}")
        self._write_to_file("CRITICAL", event, **kwargs)


# Initialize logging on module import
configure_logging()
