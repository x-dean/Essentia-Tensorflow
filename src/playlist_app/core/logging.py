"""
Logging configuration for Playlist App
Supports console and file output with structured logging and rotation
"""

import os
import sys
import logging
import logging.handlers
import json
from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from contextvars import ContextVar

# Request correlation ID for tracking requests across the system
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request correlation ID if available
        if request_id.get():
            log_entry["request_id"] = request_id.get()
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create colored output for console
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        
        color = colors.get(record.levelname, '')
        reset = '\033[0m'
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Format message
        message = f"{color}[{timestamp}] {record.levelname:8} {record.name}: {record.getMessage()}{reset}"
        
        # Add request ID if available
        if request_id.get():
            message = f"{color}[{timestamp}] {record.levelname:8} [{request_id.get()}] {record.name}: {record.getMessage()}{reset}"
        
        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True,
    structured_console: bool = False
) -> None:
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, uses default)
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        enable_console: Enable console logging
        enable_file: Enable file logging
        structured_console: Use structured JSON format for console
    """
    
    # Convert string level to logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if structured_console:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(ConsoleFormatter())
        
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if enable_file:
        if log_file is None:
            log_file = os.path.join(os.getcwd(), "logs", "playlist_app.log")
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(StructuredFormatter())
        
        root_logger.addHandler(file_handler)
    
    # Create separate log file for Essentia and TensorFlow logs
    essentia_log_file = os.path.join(os.getcwd(), "logs", "essentia_tensorflow.log")
    essentia_handler = logging.handlers.RotatingFileHandler(
        essentia_log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    essentia_handler.setLevel(logging.INFO)
    essentia_handler.setFormatter(StructuredFormatter())
    
    # Create separate loggers for Essentia and TensorFlow
    essentia_logger = logging.getLogger("essentia")
    essentia_logger.addHandler(essentia_handler)
    essentia_logger.setLevel(logging.INFO)
    essentia_logger.propagate = False  # Don't propagate to root logger
    
    tensorflow_logger = logging.getLogger("tensorflow")
    tensorflow_logger.addHandler(essentia_handler)
    tensorflow_logger.setLevel(logging.INFO)
    tensorflow_logger.propagate = False  # Don't propagate to root logger
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # Suppress verbose Essentia and TensorFlow logs
    logging.getLogger("essentia").setLevel(logging.ERROR)
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("librosa").setLevel(logging.WARNING)
    
    # Suppress FFmpeg warnings
    logging.getLogger("subprocess").setLevel(logging.WARNING)
    
    # Suppress any other verbose libraries
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)

def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs) -> None:
    """Log a message with additional context fields"""
    extra_fields = kwargs.copy()
    
    # Create a custom log record
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper()),
        "",
        0,
        message,
        (),
        None,
        func="log_with_context"
    )
    record.extra_fields = extra_fields
    
    logger.handle(record)

def set_request_id(req_id: Optional[str] = None) -> str:
    """Set request correlation ID"""
    if req_id is None:
        req_id = str(uuid.uuid4())
    request_id.set(req_id)
    return req_id

def get_request_id() -> Optional[str]:
    """Get current request correlation ID"""
    return request_id.get()

# RequestIdMiddleware temporarily disabled
# class RequestIdMiddleware:
#     """FastAPI middleware to add request correlation ID"""
#     
#     def __init__(self, app):
#         self.app = app
#     
#     async def __call__(self, scope, receive, send):
#         if scope["type"] == "http":
#             # Generate or extract request ID
#             headers = dict(scope.get("headers", []))
#             req_id = headers.get(b"x-request-id", str(uuid.uuid4()).encode())
#             if isinstance(req_id, bytes):
#                 req_id = req_id.decode()
#             
#             # Set request ID in context
#             set_request_id(req_id)
#             
#             # Add request ID to response headers
#             async def send_with_request_id(message):
#                 if message["type"] == "http.response.start":
#                     message["headers"] = message.get("headers", [])
#                     message["headers"].append((b"x-request-id", req_id.encode()))
#                 await send(message)
#             
#             await self.app(scope, receive, send_with_request_id)
#         else:
#             await self.app(scope, receive, send)

# Performance logging utilities
class PerformanceLogger:
    """Utility for logging performance metrics"""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            if exc_type:
                self.logger.error(f"Failed {self.operation} after {duration:.3f}s", exc_info=True)
            else:
                self.logger.info(f"Completed {self.operation} in {duration:.3f}s")

def log_performance(logger: logging.Logger, operation: str):
    """Decorator for logging performance of functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with PerformanceLogger(logger, operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator
# Force rebuild
