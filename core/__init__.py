"""
AgentricAI Core Package
Core system components for the AgentricAI platform.

This package provides:
- Agent loading and management
- Tool loading and execution
- Memory routing and persistence
- Conversation engine
- Event loop and workflows
- Automation system
- Configuration management
- Logging
- Validation schemas
"""

# Core components
from core.agent_loader import AgentLoader
from core.tool_loader import ToolLoader
from core.memory_router import MemoryRouter, MemoryScope, MemoryType, get_memory_router
from core.conversation_engine import ConversationEngine

# Configuration
from core.config import RuntimeConfig, get_config, reload_config

# Validation schemas
from core.schemas import (
    ChatRequest, ChatResponse,
    AgentInfo, AgentListResponse,
    ToolInfo, ToolListResponse, ToolExecuteRequest, ToolExecuteResponse,
    HealthCheckResponse, ErrorResponse
)

# Logging
from core.logging_config import (
    setup_logging, get_logger, AgentLogger, init_logging
)

# Commands
from core.commands import (
    Command, CommandRegistry, CommandCategory,
    KeyboardShortcutManager, get_command_registry
)

# Event loop
from core.event_loop import (
    Event, EventType, EventLoop, EventHandler,
    ChatEventHandler, LoggingEventHandler, get_event_loop
)

# Workflows
from core.workflows import (
    Workflow, WorkflowStep, WorkflowEngine, WorkflowStatus, StepStatus,
    get_workflow_engine
)

# Automations
from core.automations import (
    AutomationRule, AutomationEngine, Trigger, Action,
    TriggerType, ActionType, get_automation_engine
)

# Utilities
from core.utils import (
    generate_id, sanitize_filename, hash_string,
    format_bytes, format_duration, truncate_text,
    deep_merge, flatten_dict, safe_json_loads, safe_json_dumps,
    Timer, Singleton
)

# Hardware bindings
try:
    from core.hardware_bindings import (
        HardwareDetector, get_hardware_detector,
        get_gpu_info, get_cpu_info, get_ram_info,
        bind_agent_execution_mode, log_operation
    )
except ImportError:
    def get_gpu_info(): return "GPU Info Unavailable"
    def get_cpu_info(): return "CPU Info Unavailable"
    def get_ram_info(): return "RAM Info Unavailable"
    def bind_agent_execution_mode(agent_id, use_gpu=False): return f"Agent {agent_id} bound to CPU mode"
    def log_operation(agent_id, action, details): pass

# Environment
try:
    from core.environment import get_local_models
except ImportError:
    def get_local_models(): return []


__version__ = "1.0.0"

__all__ = [
    # Core components
    'AgentLoader',
    'ToolLoader',
    'MemoryRouter',
    'MemoryScope',
    'MemoryType',
    'get_memory_router',
    'ConversationEngine',
    
    # Configuration
    'RuntimeConfig',
    'get_config',
    'reload_config',
    
    # Schemas
    'ChatRequest',
    'ChatResponse',
    'AgentInfo',
    'AgentListResponse',
    'ToolInfo',
    'ToolListResponse',
    'ToolExecuteRequest',
    'ToolExecuteResponse',
    'HealthCheckResponse',
    'ErrorResponse',
    
    # Logging
    'setup_logging',
    'get_logger',
    'AgentLogger',
    'init_logging',
    
    # Commands
    'Command',
    'CommandRegistry',
    'CommandCategory',
    'KeyboardShortcutManager',
    'get_command_registry',
    
    # Event loop
    'Event',
    'EventType',
    'EventLoop',
    'EventHandler',
    'ChatEventHandler',
    'LoggingEventHandler',
    'get_event_loop',
    
    # Workflows
    'Workflow',
    'WorkflowStep',
    'WorkflowEngine',
    'WorkflowStatus',
    'StepStatus',
    'get_workflow_engine',
    
    # Automations
    'AutomationRule',
    'AutomationEngine',
    'Trigger',
    'Action',
    'TriggerType',
    'ActionType',
    'get_automation_engine',
    
    # Utilities
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
    'Timer',
    'Singleton',
    
    # Hardware
    'HardwareDetector',
    'get_hardware_detector',
    'get_gpu_info',
    'get_cpu_info',
    'get_ram_info',
    'bind_agent_execution_mode',
    'log_operation',
    
    # Environment
    'get_local_models',
    
    # Version
    '__version__'
]
