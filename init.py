"""
AgentricAI - Initialization Module
Provides runtime initialization and environment setup.
"""
import os
import sys
from pathlib import Path

# Set home directory
AGENTRICAI_HOME = Path(__file__).parent.resolve()
os.environ['AGENTRICAI_HOME'] = str(AGENTRICAI_HOME)

# Add to Python path
if str(AGENTRICAI_HOME) not in sys.path:
    sys.path.insert(0, str(AGENTRICAI_HOME))


def init_agentricai():
    """Initialize AgentricAI and return the core system."""
    from main import AgentricAIOrchestrator
    orchestrator = AgentricAIOrchestrator()
    orchestrator.init_subsystems()
    return orchestrator


def get_runtime_info():
    """Get runtime information for the current system."""
    from core.environment import get_gpu_info, get_cpu_info, get_memory_size, get_storage_info
    
    return {
        "environment_variables": {
            "AGENTRICAI_HOME": os.environ.get('AGENTRICAI_HOME', '')
        },
        "paths": {
            "python_bin": sys.executable,
            "cuda_bin": os.environ.get('CUDA_PATH', '')
        },
        "gpu_info": get_gpu_info(),
        "cpu_info": get_cpu_info(),
        "memory_size": get_memory_size(),
        "storage": get_storage_info()
    }


if __name__ == "__main__":
    # Initialize and display info
    info = get_runtime_info()
    print("AgentricAI Runtime Information:")
    print(f"  Home: {info['environment_variables']['AGENTRICAI_HOME']}")
    print(f"  Python: {info['paths']['python_bin']}")
    print(f"  CPU: {info['cpu_info']}")
    print(f"  GPU: {info['gpu_info']}")
    print(f"  Memory: {info['memory_size']} GB")
