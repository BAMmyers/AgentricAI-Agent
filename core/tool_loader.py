"""
AgentricAI Tool Loader.
Dynamic tool loading, validation, and execution with security checks.
"""
import json
import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolMetadata:
    """Metadata for a tool."""
    id: str
    name: str
    version: str
    category: str
    description: str
    execution_mode: str  # CPU, GPU, Mixed
    provenance: str
    created_at: datetime
    updated_at: datetime
    path: Path
    binary: str
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)


class ToolLoader:
    """
    Loads and validates tools from the MCP catalog.
    
    Features:
    - Tool path validation
    - Binary existence checks
    - Execution mode tracking
    - Provenance metadata
    - Safe execution with parameter validation
    """
    
    def __init__(self, catalog_path: str = "MCP_Catalog.json", tools_dir: str = None):
        """
        Initialize the tool loader.
        
        Args:
            catalog_path: Path to the MCP catalog JSON file
            tools_dir: Base directory for tools (defaults to install dir)
        """
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, ToolMetadata] = {}
        self.catalog_path = catalog_path
        self.tools_dir = Path(tools_dir) if tools_dir else Path(__file__).parent.parent / "Tools"
        self.validation_report: Dict[str, Any] = {}
        
        self.load_tools()

    def _validate_tool_path(self, tool_path: Path, binary: str) -> tuple[bool, List[str]]:
        """
        Validate that a tool path exists and is accessible.
        
        Args:
            tool_path: Path to the tool directory
            binary: Binary filename to check
            
        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []
        
        # Check directory exists
        if not tool_path.exists():
            errors.append(f"Tool directory does not exist: {tool_path}")
            return False, errors
        
        # Check binary exists
        binary_path = tool_path / binary
        if not binary_path.exists():
            errors.append(f"Binary not found: {binary_path}")
        
        # Check Python script exists (for .bat wrappers)
        if binary.endswith('.bat'):
            py_file = binary.replace('.bat', '.py')
            py_path = tool_path / py_file
            if not py_path.exists():
                errors.append(f"Python script not found: {py_path}")
        
        # Check binary is executable (on Windows, check for .bat or .exe)
        if not binary.endswith(('.bat', '.exe', '.cmd')):
            errors.append(f"Binary must be .bat, .exe, or .cmd on Windows: {binary}")
        
        return len(errors) == 0, errors

    def load_tools(self) -> Dict[str, Any]:
        """
        Load tools from the catalog with validation.
        
        Returns:
            Validation report dictionary
        """
        catalog_path = Path(self.catalog_path)
        
        if not catalog_path.is_file():
            self.validation_report = {
                "status": "error",
                "message": f"Catalog not found: {catalog_path}",
                "tools_loaded": 0,
                "tools_validated": 0,
                "errors": [f"Catalog file missing: {catalog_path}"]
            }
            return self.validation_report
        
        try:
            with open(catalog_path, "r", encoding='utf-8') as f:
                catalog = json.load(f)
        except json.JSONDecodeError as e:
            self.validation_report = {
                "status": "error",
                "message": f"Invalid JSON in catalog: {e}",
                "tools_loaded": 0,
                "tools_validated": 0,
                "errors": [str(e)]
            }
            return self.validation_report
        
        tools_data = catalog.get("MCP_Catalog", {}).get("tools", [])
        if not tools_data:
            tools_data = catalog.get("tools", [])
        
        loaded_count = 0
        validated_count = 0
        errors = []
        
        for tool in tools_data:
            tool_id = tool.get("id")
            tool_name = tool.get("name")
            binary = tool.get("binary")
            category = tool.get("category", "general")
            execution_mode = tool.get("environment_bindings", {}).get("execution_mode", "CPU")
            provenance = tool.get("provenance", "Unknown")
            version = tool.get("version", "1.0.0")
            
            if not tool_id or not binary:
                errors.append(f"Tool missing id or binary: {tool}")
                continue
            
            # Build tool path
            tool_path = self.tools_dir / tool_name if tool_name else self.tools_dir / tool_id
            
            # Validate tool
            is_valid, validation_errors = self._validate_tool_path(tool_path, binary)
            
            # Store tool info
            self.tools[tool_id] = {
                "id": tool_id,
                "name": tool_name,
                "path": str(tool_path),
                "binary": binary,
                "full_path": str(tool_path / binary),
                "category": category,
                "execution_mode": execution_mode,
                "provenance": provenance,
                "version": version,
                "validated": is_valid,
                "validation_errors": validation_errors
            }
            
            # Store metadata
            audit = tool.get("audit_metadata", {})
            self.metadata[tool_id] = ToolMetadata(
                id=tool_id,
                name=tool_name,
                version=version,
                category=category,
                description=tool.get("invocation_contract", {}).get("function_name", ""),
                execution_mode=execution_mode,
                provenance=provenance,
                created_at=datetime.fromisoformat(audit.get("created_at", "2024-01-01T00:00:00Z").replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(audit.get("updated_at", "2024-01-01T00:00:00Z").replace("Z", "+00:00")),
                path=tool_path,
                binary=binary,
                validated=is_valid,
                validation_errors=validation_errors
            )
            
            loaded_count += 1
            if is_valid:
                validated_count += 1
            else:
                errors.extend([f"{tool_id}: {e}" for e in validation_errors])
        
        self.validation_report = {
            "status": "success" if validated_count > 0 else "warning",
            "message": f"Loaded {loaded_count} tools, {validated_count} validated",
            "tools_loaded": loaded_count,
            "tools_validated": validated_count,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.validation_report

    def list_tools(self) -> List[Dict]:
        """
        List all loaded tools.
        
        Returns:
            List of tool dictionaries
        """
        return list(self.tools.values())

    def get_tool(self, tool_id: str) -> Optional[Dict]:
        """
        Get a tool by ID.
        
        Args:
            tool_id: The tool identifier
            
        Returns:
            Tool dictionary or None
        """
        return self.tools.get(tool_id)

    def get_validated_tools(self) -> List[Dict]:
        """
        Get only validated tools.
        
        Returns:
            List of validated tool dictionaries
        """
        return [t for t in self.tools.values() if t.get("validated")]

    def execute_tool(self, tool_id: str, parameters: Any = None) -> Dict[str, Any]:
        """
        Execute a tool with parameters.
        
        Args:
            tool_id: The tool identifier
            parameters: Parameters to pass to the tool
            
        Returns:
            Execution result dictionary with stdout, stderr, returncode
        """
        if tool_id not in self.tools:
            raise ValueError(f"Tool with id {tool_id} not found")
        
        tool_info = self.tools[tool_id]
        
        # Check if tool was validated
        if not tool_info.get("validated"):
            return {
                "stdout": "",
                "stderr": f"Tool validation failed: {tool_info.get('validation_errors', [])}",
                "returncode": 1,
                "error": "Tool not validated"
            }
        
        # Build command
        cmd = [tool_info["full_path"]]
        
        if isinstance(parameters, list):
            cmd.extend(str(p) for p in parameters)
        elif isinstance(parameters, dict):
            for k, v in parameters.items():
                cmd.append(str(k))
                cmd.append(str(v))
        elif parameters is not None:
            cmd.append(str(parameters))
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": True
            }
        except subprocess.CalledProcessError as e:
            return {
                "stdout": e.stdout or "",
                "stderr": e.stderr or str(e),
                "returncode": e.returncode,
                "success": False,
                "error": str(e)
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Tool execution timed out (300s)",
                "returncode": -1,
                "success": False,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "success": False,
                "error": str(e)
            }

    def get_validation_report(self) -> Dict[str, Any]:
        """Get the tool validation report."""
        return self.validation_report
