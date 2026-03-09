"""
AgentricAI Logging Configuration.
Provides structured logging with file rotation and formatting.
"""
import logging
import logging.handlers
import time
from pathlib import Path
from datetime import datetime
from typing import Optional
import json


class AgentricAILogFormatter(logging.Formatter):
    """
    Custom formatter for AgentricAI logs.
    
    Features:
    - Timestamp with milliseconds
    - Color coding for console output
    - Structured format for file logs
    """
    
    # Color codes for console output
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        """Initialize formatter with optional color support."""
        self.use_colors = use_colors
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def formatTime(self, record: logging.LogRecord, datefmt: str = None) -> str:
        """Format time with milliseconds."""
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime('%Y-%m-%d %H:%M:%S', ct)
        # Add milliseconds
        s = f"{s}.{int(record.created % 1 * 1000):03d}"
        return s

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        # Get base formatted message
        message = super().format(record)
        
        # Add colors if enabled
        if self.use_colors and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            reset = self.COLORS['RESET']
            message = f"{color}{message}{reset}"
        
        return message


class JSONLogFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'agent_id'):
            log_entry['agent_id'] = record.agent_id
        if hasattr(record, 'resource_id'):
            log_entry['resource_id'] = record.resource_id
        if hasattr(record, 'thread_id'):
            log_entry['thread_id'] = record.thread_id
        
        return json.dumps(log_entry)


def setup_logging(
    log_dir: str = None,
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    use_colors: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for AgentricAI.
    
    Args:
        log_dir: Directory for log files. Defaults to Logs/ in install dir.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        use_colors: Whether to use colors in console output
        
    Returns:
        Configured root logger
    """
    # Determine log directory
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "Logs"
    else:
        log_dir = Path(log_dir)
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(AgentricAILogFormatter(use_colors=use_colors))
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    all_logs_file = log_dir / "agentricai.log"
    file_handler = logging.handlers.RotatingFileHandler(
        all_logs_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(AgentricAILogFormatter(use_colors=False))
    root_logger.addHandler(file_handler)
    
    # JSON file handler for structured logs
    json_logs_file = log_dir / "agentricai.json.log"
    json_handler = logging.handlers.RotatingFileHandler(
        json_logs_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    json_handler.setLevel(logging.INFO)
    json_handler.setFormatter(JSONLogFormatter())
    root_logger.addHandler(json_handler)
    
    # Error-only file handler
    error_logs_file = log_dir / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_logs_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(AgentricAILogFormatter(use_colors=False))
    root_logger.addHandler(error_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class AgentLogger:
    """
    Context-aware logger for agent operations.
    
    Provides methods for logging agent-specific events with context.
    """
    
    def __init__(self, agent_id: str, logger_name: str = None):
        """
        Initialize agent logger.
        
        Args:
            agent_id: The agent's identifier
            logger_name: Optional logger name (defaults to agent_id)
        """
        self.agent_id = agent_id
        self.logger = logging.getLogger(logger_name or f"agent.{agent_id}")
    
    def _log(self, level: str, message: str, **kwargs):
        """Log with extra context."""
        extra = {'agent_id': self.agent_id}
        extra.update(kwargs)
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log('critical', message, **kwargs)
    
    def log_conversation(self, resource_id: str, thread_id: str, 
                         role: str, content: str):
        """Log a conversation event."""
        self.info(
            f"Conversation: [{role}] {content[:100]}...",
            resource_id=resource_id,
            thread_id=thread_id
        )
    
    def log_tool_execution(self, tool_id: str, parameters: dict, result: str):
        """Log a tool execution event."""
        self.info(
            f"Tool executed: {tool_id}",
            tool_id=tool_id,
            parameters=str(parameters)[:200],
            result=result[:200]
        )
    
    def log_memory_operation(self, operation: str, key: str, scope: str):
        """Log a memory operation."""
        self.debug(
            f"Memory {operation}: {key} ({scope})",
            operation=operation,
            memory_key=key,
            memory_scope=scope
        )


# Initialize logging on module import
_logger = None

def init_logging(**kwargs) -> logging.Logger:
    """Initialize logging with optional configuration."""
    global _logger
    if _logger is None:
        _logger = setup_logging(**kwargs)
    return _logger
