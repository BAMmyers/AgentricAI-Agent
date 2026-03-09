"""
AgentricAI Utility Functions.
Common utilities used across the codebase.
"""
import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for use as a filename.
    
    Args:
        name: The string to sanitize
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    # Limit length
    return sanitized[:255] if sanitized else 'unnamed'


def hash_string(text: str) -> str:
    """Generate SHA-256 hash of a string."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def format_bytes(size: int) -> str:
    """
    Format bytes as human-readable string.
    
    Args:
        size: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration as human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "2h 30m")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Dictionary to merge into base
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def safe_json_loads(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON string.
    
    Args:
        text: JSON string to parse
        default: Default value on error
        
    Returns:
        Parsed value or default
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely serialize to JSON.
    
    Args:
        obj: Object to serialize
        default: Default value on error
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return default


def is_valid_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split a list into chunks.
    
    Args:
        lst: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def get_nested_value(d: Dict, keys: str, default: Any = None) -> Any:
    """
    Get a nested value from a dictionary using dot notation.
    
    Args:
        d: Dictionary to search
        keys: Dot-separated key path (e.g., "user.profile.name")
        default: Default value if not found
        
    Returns:
        Found value or default
    """
    keys_list = keys.split('.')
    result = d
    
    for key in keys_list:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default
    
    return result


def set_nested_value(d: Dict, keys: str, value: Any) -> Dict:
    """
    Set a nested value in a dictionary using dot notation.
    
    Args:
        d: Dictionary to modify
        keys: Dot-separated key path
        value: Value to set
        
    Returns:
        Modified dictionary
    """
    keys_list = keys.split('.')
    current = d
    
    for key in keys_list[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys_list[-1]] = value
    return d


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_file_hash(filepath: Union[str, Path]) -> str:
    """
    Get SHA-256 hash of a file.
    
    Args:
        filepath: Path to file
        
    Returns:
        Hash string
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def read_file_safe(filepath: Union[str, Path], default: str = "") -> str:
    """
    Safely read a file.
    
    Args:
        filepath: Path to file
        default: Default value on error
        
    Returns:
        File contents or default
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError):
        return default


def write_file_safe(filepath: Union[str, Path], content: str) -> bool:
    """
    Safely write to a file.
    
    Args:
        filepath: Path to file
        content: Content to write
        
    Returns:
        True if successful
    """
    try:
        ensure_directory(Path(filepath).parent)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except (IOError, OSError):
        return False


class Timer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, *args):
        self.end_time = datetime.now()
        self.elapsed = (self.end_time - self.start_time).total_seconds()
    
    def __str__(self) -> str:
        if self.elapsed is not None:
            return f"{self.name}: {format_duration(self.elapsed)}"
        return f"{self.name}: running..."


class Singleton:
    """Singleton metaclass."""
    
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


# Export all utilities
__all__ = [
    'generate_id',
    'sanitize_filename',
    'hash_string',
    'format_bytes',
    'format_duration',
    'truncate_text',
    'deep_merge',
    'flatten_dict',
    'safe_json_loads',
    'safe_json_dumps',
    'is_valid_uuid',
    'chunk_list',
    'get_nested_value',
    'set_nested_value',
    'ensure_directory',
    'get_file_hash',
    'read_file_safe',
    'write_file_safe',
    'Timer',
    'Singleton'
]
