"""
AgentricAI Agent Loader.
Dynamic agent discovery, loading, and validation.
"""
from importlib.util import spec_from_file_location, module_from_spec
import inspect
import os
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentValidationResult:
    """Result of agent validation."""
    valid: bool
    agent_id: str
    errors: List[str]
    warnings: List[str]


class AgentLoader:
    """
    Loads and validates agents from the agents directory.
    
    Features:
    - Dynamic agent discovery
    - Agent validation (id, name, model attributes)
    - Error handling for malformed agents
    - Agent lifecycle management
    """
    
    def __init__(self, agents_dir: str = None):
        """
        Initialize the agent loader.
        
        Args:
            agents_dir: Directory to load agents from
        """
        self.agents: Dict[str, Any] = {}
        self.validation_results: Dict[str, AgentValidationResult] = {}
        self.agents_dir = agents_dir or "core/agents"
        self.load_agents()
    
    def _validate_agent(self, agent_instance: Any) -> AgentValidationResult:
        """
        Validate an agent instance.
        
        Checks for:
        - Required attributes (id, name)
        - Recommended attributes (model, memory_config)
        - Method existence (generate_response, stream_response)
        
        Args:
            agent_instance: The agent instance to validate
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        agent_id = getattr(agent_instance, 'id', 'unknown')
        
        # Required attributes
        if not hasattr(agent_instance, 'id'):
            errors.append("Missing required attribute: 'id'")
        elif not isinstance(agent_instance.id, str) or not agent_instance.id:
            errors.append("Agent 'id' must be a non-empty string")
        
        if not hasattr(agent_instance, 'name'):
            errors.append("Missing required attribute: 'name'")
        elif not isinstance(agent_instance.name, str) or not agent_instance.name:
            errors.append("Agent 'name' must be a non-empty string")
        
        # Recommended attributes
        if not hasattr(agent_instance, 'model'):
            warnings.append("Missing recommended attribute: 'model'")
        elif not isinstance(agent_instance.model, str):
            warnings.append("Agent 'model' should be a string")
        
        if not hasattr(agent_instance, 'memory_config'):
            warnings.append("Missing recommended attribute: 'memory_config'")
        
        # Required methods
        if not hasattr(agent_instance, 'generate_response'):
            errors.append("Missing required method: 'generate_response'")
        elif not callable(agent_instance.generate_response):
            errors.append("'generate_response' must be a callable method")
        
        if not hasattr(agent_instance, 'stream_response'):
            warnings.append("Missing recommended method: 'stream_response'")
        
        return AgentValidationResult(
            valid=len(errors) == 0,
            agent_id=agent_id,
            errors=errors,
            warnings=warnings
        )
    
    def load_agents(self, directory: str = None) -> Dict[str, AgentValidationResult]:
        """
        Load all agents from a directory.
        
        Args:
            directory: Directory to load from (uses self.agents_dir if not specified)
            
        Returns:
            Dictionary of validation results
        """
        directory = directory or self.agents_dir
        
        if not os.path.exists(directory):
            print(f"[AgentLoader] Warning: Agents directory not found: {directory}")
            return self.validation_results
        
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    module_path = os.path.join(root, file)
                    self._load_module(module_path)
        
        return self.validation_results
    
    def _load_module(self, module_path: str):
        """Load agents from a single module."""
        try:
            module_name = module_path.replace("/", ".").replace("\\", ".")
            spec = spec_from_file_location(module_name, module_path)
            
            if spec is None or spec.loader is None:
                return
            
            module = module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find and validate agent classes
            for attr in dir(module):
                try:
                    obj = getattr(module, attr)
                    
                    if not inspect.isclass(obj):
                        continue
                    
                    # Check for agent attributes
                    if not hasattr(obj, 'id') and not hasattr(obj, 'name'):
                        continue
                    
                    # Skip base classes
                    if obj.__name__ in ('MemoryScopedAgent', 'Agent', 'object'):
                        continue
                    
                    # Instantiate and validate
                    try:
                        instance = obj()
                        validation = self._validate_agent(instance)
                        self.validation_results[instance.id] = validation
                        
                        if validation.valid:
                            self.agents[instance.id] = instance
                            if validation.warnings:
                                print(f"[AgentLoader] Loaded {instance.id} with warnings: {validation.warnings}")
                        else:
                            print(f"[AgentLoader] Invalid agent {instance.id}: {validation.errors}")
                    
                    except Exception as e:
                        print(f"[AgentLoader] Failed to instantiate {obj.__name__}: {e}")
                
                except Exception as e:
                    print(f"[AgentLoader] Error processing attribute {attr}: {e}")
        
        except Exception as e:
            print(f"[AgentLoader] Failed to load module {module_path}: {e}")
    
    def list_agents(self) -> List[Dict]:
        """
        List all loaded agents.
        
        Returns:
            List of agent metadata dictionaries
        """
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "model": getattr(agent, "model", None),
                "memory_config": getattr(agent, "memory_config", None),
                "version": getattr(agent, "version", "1.0.0"),
                "validated": self.validation_results.get(agent.id, AgentValidationResult(False, agent.id, [], [])).valid
            }
            for agent in self.agents.values()
        ]
    
    def get_agent(self, agent_id: str):
        """
        Get an agent by ID.
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            The agent instance
            
        Raises:
            ValueError: If agent not found
        """
        if agent_id in self.agents:
            return self.agents[agent_id]
        raise ValueError(f"Agent with id '{agent_id}' not found. Available agents: {list(self.agents.keys())}")
    
    def create_agent(self, config: Dict) -> str:
        """
        Create a new agent from configuration.
        
        Args:
            config: Agent configuration with 'class' and 'module' keys
            
        Returns:
            The created agent's ID
        """
        agent_class = config.get("class")
        if not agent_class:
            raise ValueError("Missing agent class in config")
        
        module_path = config.get("module")
        if not module_path:
            raise ValueError("Missing module path in config")
        
        spec = spec_from_file_location(module_path, module_path)
        module = module_from_spec(spec)
        sys.modules[module_path] = module
        spec.loader.exec_module(module)
        
        cls = getattr(module, agent_class)
        instance = cls()
        
        # Validate before adding
        validation = self._validate_agent(instance)
        if not validation.valid:
            raise ValueError(f"Invalid agent: {validation.errors}")
        
        self.agents[instance.id] = instance
        self.validation_results[instance.id] = validation
        
        return instance.id
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent.
        
        Args:
            agent_id: The agent to delete
            
        Returns:
            True if deleted
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.validation_results.pop(agent_id, None)
            return True
        raise ValueError(f"Agent with id '{agent_id}' not found")
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get a validation report for all agents."""
        return {
            "total_agents": len(self.agents),
            "valid_agents": sum(1 for v in self.validation_results.values() if v.valid),
            "invalid_agents": sum(1 for v in self.validation_results.values() if not v.valid),
            "details": {
                agent_id: {
                    "valid": result.valid,
                    "errors": result.errors,
                    "warnings": result.warnings
                }
                for agent_id, result in self.validation_results.items()
            }
        }
