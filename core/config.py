"""
AgentricAI Configuration Module.
Provides centralized configuration management with environment variable support.
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class RuntimeConfig:
    """
    Runtime configuration for AgentricAI.
    
    Supports:
    - Environment variable overrides
    - Configuration file loading
    - Default values
    """
    # API Configuration
    host: str = "127.0.0.1"
    api_port: int = 3939
    ui_port: int = 3000
    
    # Ollama Configuration
    ollama_url: str = "http://localhost:11434"
    default_model: str = "lacy:latest"
    
    # Memory Configuration
    memory_db_path: str = "memory.db"
    max_conversation_history: int = 20
    
    # Cache & Distributed
    redis_url: str = "redis://localhost:6379"
    deployment_mode: str = "standalone"  # standalone|distributed
    instance_id: str = "instance-1"
    
    # Celery / Background Tasks
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # Timeouts
    stream_timeout_seconds: int = 120
    request_timeout_seconds: int = 300
    
    # Compression
    enable_gzip: bool = True
    gzip_minimum_size: int = 1024
    
    # Logging
    log_level: str = "INFO"
    
    # API / CORS
    cors_origins: List[str] = field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    
    @property
    def api_url(self) -> str:
        """Get the full API URL."""
        return f"http://{self.host}:{self.api_port}"
    
    @property
    def ui_url(self) -> str:
        """Get the full UI URL."""
        return f"http://{self.host}:{self.ui_port}"
    
    @classmethod
    def from_env(cls) -> 'RuntimeConfig':
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("AGENTRIC_HOST", "127.0.0.1"),
            api_port=int(os.getenv("AGENTRIC_API_PORT", "3939")),
            ui_port=int(os.getenv("AGENTRIC_UI_PORT", "3000")),
            ollama_url=os.getenv("AGENTRIC_OLLAMA_URL", "http://localhost:11434"),
            default_model=os.getenv("AGENTRIC_DEFAULT_MODEL", "lacy:latest"),
            memory_db_path=os.getenv("AGENTRIC_MEMORY_DB", "memory.db"),
            max_conversation_history=int(os.getenv("AGENTRIC_MAX_HISTORY", "20")),
            stream_timeout_seconds=int(os.getenv("AGENTRIC_STREAM_TIMEOUT", "120")),
            request_timeout_seconds=int(os.getenv("AGENTRIC_REQUEST_TIMEOUT", "300")),
            redis_url=os.getenv("AGENTRIC_REDIS_URL", "redis://localhost:6379"),
            deployment_mode=os.getenv("AGENTRIC_DEPLOYMENT_MODE", "standalone"),
            instance_id=os.getenv("AGENTRIC_INSTANCE_ID", "instance-1"),
            celery_broker_url=os.getenv("AGENTRIC_CELERY_BROKER", "redis://localhost:6379/0"),
            celery_result_backend=os.getenv("AGENTRIC_CELERY_BACKEND", "redis://localhost:6379/1"),
            enable_gzip=os.getenv("AGENTRIC_ENABLE_GZIP", "true").lower() in ["1","true","yes"],
            gzip_minimum_size=int(os.getenv("AGENTRIC_GZIP_MIN_SIZE", "1024")),
            log_level=os.getenv("AGENTRIC_LOG_LEVEL", "INFO"),
            cors_origins=[
                origin.strip()
                for origin in os.getenv(
                    "AGENTRIC_CORS_ORIGINS",
                    "http://localhost:3000,http://127.0.0.1:3000",
                ).split(",")
                if origin.strip()
            ],
        )
    
    @classmethod
    def from_file(cls, path: str) -> 'RuntimeConfig':
        """Load configuration from JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            return cls()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        runtime = data.get('runtime', {})
        api = data.get('api', {})
        return cls(
            host=runtime.get('host', '127.0.0.1'),
            api_port=runtime.get('api_port', 3939),
            ui_port=runtime.get('ui_port', 3000),
            ollama_url=runtime.get('ollama_url', 'http://localhost:11434'),
            default_model=runtime.get('default_model', 'lacy:latest'),
            memory_db_path=runtime.get('memory_db_path', 'memory.db'),
            max_conversation_history=runtime.get('max_conversation_history', 20),
            stream_timeout_seconds=runtime.get('stream_timeout_seconds', 120),
            request_timeout_seconds=runtime.get('request_timeout_seconds', 300),
            redis_url=runtime.get('redis_url', 'redis://localhost:6379'),
            deployment_mode=runtime.get('deployment_mode', 'standalone'),
            instance_id=runtime.get('instance_id', 'instance-1'),
            celery_broker_url=runtime.get('celery_broker_url', 'redis://localhost:6379/0'),
            celery_result_backend=runtime.get('celery_result_backend', 'redis://localhost:6379/1'),
            enable_gzip=runtime.get('enable_gzip', True),
            gzip_minimum_size=runtime.get('gzip_minimum_size', 1024),
            log_level=data.get('logging', {}).get('level', 'INFO'),
            cors_origins=api.get(
                'cors_origins',
                [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ],
            ),
        )


# Global configuration instance
_config: Optional[RuntimeConfig] = None


def get_config() -> RuntimeConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        # Try to load from file first, then env
        config_file = Path(__file__).parent.parent / "runtime.json"
        if config_file.exists():
            _config = RuntimeConfig.from_file(str(config_file))
        else:
            _config = RuntimeConfig.from_env()
    return _config


def reload_config() -> RuntimeConfig:
    """Reload configuration from sources."""
    global _config
    _config = None
    return get_config()
