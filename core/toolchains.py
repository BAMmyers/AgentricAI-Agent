"""
AgentricAI - Toolchains System
Dynamic tool loading and execution for agents.
"""
import os
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional


class Tool:
    """Represents a single tool that can be executed by agents."""
    
    def __init__(self, id: str, name: str, description: str, handler: Callable, parameters: Dict = None):
        self.id = id
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters or {}
    
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return self.handler(**kwargs)


class Toolchain:
    """A chain of tools that can be executed in sequence."""
    
    def __init__(self, id: str, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description
        self.tools: List[Tool] = []
        self.execution_order: List[str] = []
    
    def add_tool(self, tool: Tool, position: int = None):
        """Add a tool to the chain."""
        if position is None:
            self.tools.append(tool)
            self.execution_order.append(tool.id)
        else:
            self.tools.insert(position, tool)
            self.execution_order.insert(position, tool.id)
    
    def remove_tool(self, tool_id: str):
        """Remove a tool from the chain."""
        self.tools = [t for t in self.tools if t.id != tool_id]
        self.execution_order = [tid for tid in self.execution_order if tid != tool_id]
    
    async def execute(self, context: Dict = None) -> Dict:
        """Execute all tools in the chain sequentially."""
        results = {}
        ctx = context or {}
        
        for tool_id in self.execution_order:
            tool = next((t for t in self.tools if t.id == tool_id), None)
            if tool:
                try:
                    result = tool.execute(**{**ctx, **results})
                    results[tool_id] = result
                    ctx = {**ctx, 'previous_result': result}
                except Exception as e:
                    results[tool_id] = {'error': str(e)}
        
        return results


class ToolchainManager:
    """Manages all toolchains for the AgentricAI system."""
    
    def __init__(self, toolchains_dir: str = None):
        self.toolchains: Dict[str, Toolchain] = {}
        self.tools: Dict[str, Tool] = {}
        self.toolchains_dir = Path(toolchains_dir) if toolchains_dir else Path(__file__).parent / 'toolchains'
        
        # Register built-in tools
        self._register_builtin_tools()
        
        # Load toolchains from directory
        self.load_toolchains()
    
    def _register_builtin_tools(self):
        """Register built-in tools."""
        
        # Code Execution Tool
        self.register_tool(Tool(
            id='code_execute',
            name='Code Execution',
            description='Execute Python code safely',
            handler=self._execute_code,
            parameters={
                'code': {'type': 'string', 'required': True},
                'language': {'type': 'string', 'default': 'python'}
            }
        ))
        
        # File Read Tool
        self.register_tool(Tool(
            id='file_read',
            name='File Read',
            description='Read contents of a file',
            handler=self._read_file,
            parameters={
                'path': {'type': 'string', 'required': True}
            }
        ))
        
        # File Write Tool
        self.register_tool(Tool(
            id='file_write',
            name='File Write',
            description='Write content to a file',
            handler=self._write_file,
            parameters={
                'path': {'type': 'string', 'required': True},
                'content': {'type': 'string', 'required': True}
            }
        ))
        
        # Web Search Tool
        self.register_tool(Tool(
            id='web_search',
            name='Web Search',
            description='Search the web for information',
            handler=self._web_search,
            parameters={
                'query': {'type': 'string', 'required': True}
            }
        ))
        
        # Memory Store Tool
        self.register_tool(Tool(
            id='memory_store',
            name='Memory Store',
            description='Store information in agent memory',
            handler=self._memory_store,
            parameters={
                'key': {'type': 'string', 'required': True},
                'value': {'type': 'any', 'required': True}
            }
        ))
        
        # Memory Retrieve Tool
        self.register_tool(Tool(
            id='memory_retrieve',
            name='Memory Retrieve',
            description='Retrieve information from agent memory',
            handler=self._memory_retrieve,
            parameters={
                'key': {'type': 'string', 'required': True}
            }
        ))
    
    def register_tool(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.id] = tool
    
    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self.tools.get(tool_id)
    
    def list_tools(self) -> List[Dict]:
        """List all available tools."""
        return [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'parameters': t.parameters
            }
            for t in self.tools.values()
        ]
    
    def create_toolchain(self, id: str, name: str, description: str) -> Toolchain:
        """Create a new toolchain."""
        chain = Toolchain(id, name, description)
        self.toolchains[id] = chain
        return chain
    
    def get_toolchain(self, chain_id: str) -> Optional[Toolchain]:
        """Get a toolchain by ID."""
        return self.toolchains.get(chain_id)
    
    def list_toolchains(self) -> List[Dict]:
        """List all available toolchains."""
        return [
            {
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'tools': c.execution_order
            }
            for c in self.toolchains.values()
        ]
    
    def load_toolchains(self):
        """Load toolchains from directory."""
        if not self.toolchains_dir.exists():
            self.toolchains_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for file in self.toolchains_dir.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                chain = self.create_toolchain(
                    data.get('id', file.stem),
                    data.get('name', file.stem),
                    data.get('description', '')
                )
                
                for tool_ref in data.get('tools', []):
                    tool_id = tool_ref.get('id')
                    if tool_id in self.tools:
                        chain.add_tool(self.tools[tool_id])
                
            except Exception as e:
                print(f"Error loading toolchain {file}: {e}")
    
    # Built-in tool handlers
    def _execute_code(self, code: str, language: str = 'python', **kwargs):
        """Execute Python code safely."""
        try:
            # Create a restricted execution environment
            local_vars = {}
            exec(code, {"__builtins__": {}}, local_vars)
            return {"success": True, "result": local_vars}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _read_file(self, path: str, **kwargs):
        """Read file contents."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _write_file(self, path: str, content: str, **kwargs):
        """Write content to file."""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _web_search(self, query: str, **kwargs):
        """Search the web (placeholder)."""
        # TODO: Implement actual web search
        return {"success": True, "results": [], "query": query}
    
    def _memory_store(self, key: str, value: Any, **kwargs):
        """Store in memory (placeholder)."""
        # TODO: Connect to memory router
        return {"success": True, "key": key}
    
    def _memory_retrieve(self, key: str, **kwargs):
        """Retrieve from memory (placeholder)."""
        # TODO: Connect to memory router
        return {"success": True, "key": key, "value": None}


# Global toolchain manager instance
_toolchain_manager = None

def get_toolchain_manager() -> ToolchainManager:
    """Get the global toolchain manager instance."""
    global _toolchain_manager
    if _toolchain_manager is None:
        _toolchain_manager = ToolchainManager()
    return _toolchain_manager
