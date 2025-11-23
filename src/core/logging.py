"""
Centralized Logging Configuration
Provides structured logging with JSON output support for production
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
from pathlib import Path

from .config import get_settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Enhanced text formatter with colors for development"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build log line
        log_line = (
            f"{color}{record.levelname:8s}{reset} "
            f"[{timestamp}] "
            f"{record.name}:{record.lineno} - "
            f"{record.getMessage()}"
        )
        
        # Add exception if present
        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"
        
        return log_line


def setup_logging(name: str = None) -> logging.Logger:
    """
    Setup application logging with proper configuration
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Get or create logger
    logger = logging.getLogger(name or "innerverse")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Choose formatter based on configuration
    if settings.LOG_FORMAT == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(JSONFormatter())  # Always use JSON for files
        logger.addHandler(file_handler)
    
    return logger


# Create default logger
logger = setup_logging("innerverse")


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log message with additional context fields
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields to include
    """
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper()),
        "(unknown file)",
        0,
        message,
        (),
        None
    )
    record.extra_fields = context
    logger.handle(record)

