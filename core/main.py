"""
AgentricAI Core System - Main Module
Initializes and manages the core system components:
- Agent Loader
- Tool Loader
- Memory Router
- Conversation Engine
- Hardware Bindings
"""
import os
import sys
from pathlib import Path

# Add paths
CORE_DIR = Path(__file__).parent.resolve()
ROOT_DIR = CORE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.agent_loader import AgentLoader
from core.tool_loader import ToolLoader
from core.memory_router import MemoryRouter
from core.conversation_engine import ConversationEngine
from core.environment import get_gpu_info, get_cpu_info, get_ram_info, get_local_models

# Try to import hardware bindings, use fallback if not available
try:
    from core.hardware_bindings import bind_agent_execution_mode, log_operation
except ImportError:
    def bind_agent_execution_mode(agent_id, use_gpu=False):
        return f"Agent {agent_id} bound to CPU execution mode"
    def log_operation(agent_id, action, details):
        pass


class CoreSystem:
    """Core system container for all AgentricAI components."""
    
    def __init__(self):
        self._initialized = False
        self.agent_loader = None
        self.tool_loader = None
        self.memory_router = None
        self.conversation_engine = None
        self.hardware_info = {}
        
        print("[Core] Initializing AgentricAI Core System...")
        
        # Gather hardware info
        self.hardware_info = {
            "gpu": get_gpu_info(),
            "cpu": get_cpu_info(),
            "ram": get_ram_info(),
            "models": get_local_models()
        }
        print(f"[Core] Hardware: {self.hardware_info['cpu']}")
        print(f"[Core] GPU: {self.hardware_info['gpu']}")
        
        # Initialize loaders
        print("[Core] Loading agents...")
        self.agent_loader = AgentLoader()
        print(f"[Core] Loaded {len(self.agent_loader.agents)} agents")
        
        print("[Core] Loading tools...")
        self.tool_loader = ToolLoader()
        print(f"[Core] Loaded {len(self.tool_loader.tools)} tools")
        
        print("[Core] Initializing memory router...")
        self.memory_router = MemoryRouter()
        
        print("[Core] Initializing conversation engine...")
        self.conversation_engine = ConversationEngine(
            self.agent_loader,
            self.tool_loader,
            self.memory_router
        )
        
        self._initialized = True
        print("[Core] Core System initialized successfully")
        
    def get_agent(self, agent_id):
        """Get an agent by ID."""
        return self.agent_loader.get_agent(agent_id)
        
    def list_agents(self):
        """List all available agents."""
        return self.agent_loader.list_agents()
        
    def list_tools(self):
        """List all available tools."""
        return self.tool_loader.list_tools()
        
    def read_memory(self, resource, thread):
        """Read memory for a resource/thread."""
        return self.memory_router.read_memory(resource, thread)
        
    def write_memory(self, resource, thread, content):
        """Write memory for a resource/thread."""
        return self.memory_router.write_memory(resource, thread, content)


def init_core() -> CoreSystem:
    """Initialize and return the core system."""
    core = CoreSystem()
    
    print("-" * 40)
    print("AgentricAI Core System Ready")
    print(f"Agents: {len(core.list_agents())}")
    print(f"Tools: {len(core.list_tools())}")
    print("-" * 40)
    
    return core


if __name__ == "__main__":
    core = init_core()
    print(f"Agents: {core.list_agents()}")
    print(f"Tools: {core.list_tools()}")
