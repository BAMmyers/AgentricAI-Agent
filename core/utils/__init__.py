# Core Utils Package
# Re-export everything from core/utils.py module
# This allows both 'from core.utils import X' and 'from core import utils' to work

import sys
from pathlib import Path

# Import the utils.py module from parent directory
# We need to import it as a different name to avoid circular issues
_import_path = Path(__file__).parent.parent / "utils.py"
_module_name = "core._utils_module"

import importlib.util
spec = importlib.util.spec_from_file_location(_module_name, _import_path)
_utils_module = importlib.util.module_from_spec(spec)
sys.modules[_module_name] = _utils_module
spec.loader.exec_module(_utils_module)

# Re-export all public names
from core._utils_module import (
    generate_id, sanitize_filename, hash_string,
    format_bytes, format_duration, truncate_text,
    deep_merge, flatten_dict, safe_json_loads, safe_json_dumps,
    is_valid_uuid, chunk_list, get_nested_value, set_nested_value,
    ensure_directory, get_file_hash, read_file_safe, write_file_safe,
    Timer, Singleton
)

__all__ = [
    'generate_id', 'sanitize_filename', 'hash_string',
    'format_bytes', 'format_duration', 'truncate_text',
    'deep_merge', 'flatten_dict', 'safe_json_loads', 'safe_json_dumps',
    'is_valid_uuid', 'chunk_list', 'get_nested_value', 'set_nested_value',
    'ensure_directory', 'get_file_hash', 'read_file_safe', 'write_file_safe',
    'Timer', 'Singleton'
]
