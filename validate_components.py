#!/usr/bin/env python3
"""
AgentricAI Validation Script
Tests all 5 components for launch.bat integration

Components:
1. launch.bat - Startup script
2. launch_gpu.bat - GPU-enabled startup
3. UI/package.json - Next.js frontend
4. Tools/ - Tool stubs
5. Core system - Python backend
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime


class AgentricAIValidator:
    """Validates all AgentricAI components."""
    
    def __init__(self):
        self.root = Path(r"C:\Program Files\AgentricAI")
        self.results = {}
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def log(self, component: str, status: str, message: str):
        """Log a validation result."""
        if component not in self.results:
            self.results[component] = []
        self.results[component].append({
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!"
        print(f"  [{symbol}] {message}")
        
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        else:
            self.warnings += 1
    
    def validate_launch_bat(self):
        """Validate launch.bat component."""
        print("\n[1/5] Validating launch.bat...")
        component = "launch.bat"
        
        launch_bat = self.root / "launch.bat"
        
        # Check file exists
        if launch_bat.exists():
            self.log(component, "PASS", "launch.bat exists")
        else:
            self.log(component, "FAIL", "launch.bat not found")
            return
        
        # Read content
        content = launch_bat.read_text(encoding='utf-8')
        
        # Check for required components
        checks = [
            ("PYTHONPATH", "PYTHONPATH configuration"),
            ("python_embedded", "Embedded Python path"),
            ("Ollama", "Ollama service check"),
            ("main.py", "Main orchestrator execution"),
            ("AGENTRICAI_ROOT", "Root directory variable"),
            ("AGENTRICAI_PORT", "Port configuration"),
            ("UI", "UI startup"),
            ("npm", "npm commands"),
            ("health", "Health check"),
        ]
        
        for keyword, desc in checks:
            if keyword.lower() in content.lower():
                self.log(component, "PASS", f"Contains {desc}")
            else:
                self.log(component, "WARN", f"Missing {desc}")
        
        # Check for all 5 components
        components = ["API", "Ollama", "UI", "Docs", "Prerequisites"]
        for comp in components:
            if comp.lower() in content.lower():
                self.log(component, "PASS", f"Handles {comp} component")
            else:
                self.log(component, "WARN", f"May not handle {comp} component")
    
    def validate_launch_gpu_bat(self):
        """Validate launch_gpu.bat component."""
        print("\n[2/5] Validating launch_gpu.bat...")
        component = "launch_gpu.bat"
        
        launch_gpu = self.root / "launch_gpu.bat"
        
        if launch_gpu.exists():
            self.log(component, "PASS", "launch_gpu.bat exists")
        else:
            self.log(component, "FAIL", "launch_gpu.bat not found")
            return
        
        content = launch_gpu.read_text(encoding='utf-8')
        
        # GPU-specific checks
        gpu_checks = [
            ("CUDA_VISIBLE_DEVICES", "CUDA device configuration"),
            ("GPU", "GPU mode flag"),
            ("OLLAMA_GPU_LAYERS", "Ollama GPU layers"),
            ("nvidia-smi", "NVIDIA GPU detection"),
            ("GPU_MODE", "GPU mode environment variable"),
        ]
        
        for keyword, desc in gpu_checks:
            if keyword in content:
                self.log(component, "PASS", f"Contains {desc}")
            else:
                self.log(component, "WARN", f"Missing {desc}")
    
    def validate_ui_package(self):
        """Validate UI/package.json component."""
        print("\n[3/5] Validating UI/package.json...")
        component = "UI/package.json"
        
        package_json = self.root / "UI" / "package.json"
        
        if package_json.exists():
            self.log(component, "PASS", "UI/package.json exists")
        else:
            self.log(component, "FAIL", "UI/package.json not found")
            return
        
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            
            self.log(component, "PASS", "package.json is valid JSON")
            
            # Check required fields
            required = ["name", "version", "scripts", "dependencies"]
            for field in required:
                if field in pkg:
                    self.log(component, "PASS", f"Has {field} field")
                else:
                    self.log(component, "FAIL", f"Missing {field} field")
            
            # Check scripts
            if "scripts" in pkg:
                for script in ["dev", "build", "start"]:
                    if script in pkg["scripts"]:
                        self.log(component, "PASS", f"Has {script} script")
                    else:
                        self.log(component, "WARN", f"Missing {script} script")
            
            # Check dependencies
            if "dependencies" in pkg:
                for dep in ["next", "react", "react-dom"]:
                    if dep in pkg["dependencies"]:
                        self.log(component, "PASS", f"Has {dep} dependency")
                    else:
                        self.log(component, "WARN", f"Missing {dep} dependency")
                        
        except json.JSONDecodeError as e:
            self.log(component, "FAIL", f"Invalid JSON: {e}")
    
    def validate_tools(self):
        """Validate Tools/ directory and tool stubs."""
        print("\n[4/5] Validating Tools/...")
        component = "Tools"
        
        tools_dir = self.root / "Tools"
        
        if tools_dir.exists():
            self.log(component, "PASS", "Tools directory exists")
        else:
            self.log(component, "FAIL", "Tools directory not found")
            return
        
        # Check MCP_Catalog.json
        catalog_path = self.root / "MCP_Catalog.json"
        if catalog_path.exists():
            self.log(component, "PASS", "MCP_Catalog.json exists")
            
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
                
                tools = catalog.get("MCP_Catalog", {}).get("tools", [])
                self.log(component, "PASS", f"Found {len(tools)} tools in catalog")
                
                # Check each tool
                for tool in tools:
                    tool_name = tool.get("name", "Unknown")
                    tool_path = tool.get("environment_bindings", {}).get("path", "")
                    
                    if tool_path:
                        tool_dir = Path(tool_path)
                        if tool_dir.exists():
                            self.log(component, "PASS", f"Tool directory exists: {tool_name}")
                            
                            # Check for binaries
                            binaries = tool.get("environment_bindings", {}).get("binaries", [])
                            for binary in binaries:
                                binary_path = tool_dir / binary
                                if binary_path.exists():
                                    self.log(component, "PASS", f"Binary exists: {binary}")
                                else:
                                    self.log(component, "WARN", f"Binary missing: {binary}")
                        else:
                            self.log(component, "FAIL", f"Tool directory missing: {tool_name}")
                            
            except json.JSONDecodeError as e:
                self.log(component, "FAIL", f"Invalid MCP_Catalog.json: {e}")
        else:
            self.log(component, "FAIL", "MCP_Catalog.json not found")
    
    def validate_core_system(self):
        """Validate core Python backend."""
        print("\n[5/5] Validating Core System...")
        component = "Core"
        
        # Check main.py
        main_py = self.root / "main.py"
        if main_py.exists():
            self.log(component, "PASS", "main.py exists")
        else:
            self.log(component, "FAIL", "main.py not found")
        
        # Check core directory
        core_dir = self.root / "core"
        if core_dir.exists():
            self.log(component, "PASS", "core directory exists")
        else:
            self.log(component, "FAIL", "core directory not found")
            return
        
        # Check core files
        core_files = [
            "main.py",
            "agent_loader.py",
            "tool_loader.py",
            "memory_router.py",
            "conversation_engine.py",
            "environment.py",
        ]
        
        for file in core_files:
            file_path = core_dir / file
            if file_path.exists():
                self.log(component, "PASS", f"core/{file} exists")
            else:
                self.log(component, "FAIL", f"core/{file} missing")
        
        # Check api directory
        api_dir = self.root / "api"
        if api_dir.exists():
            self.log(component, "PASS", "api directory exists")
            
            api_main = api_dir / "main.py"
            if api_main.exists():
                self.log(component, "PASS", "api/main.py exists")
            else:
                self.log(component, "FAIL", "api/main.py missing")
        else:
            self.log(component, "FAIL", "api directory missing")
        
        # Check embedded Python
        python_exe = self.root / "python_embedded" / "python.exe"
        if python_exe.exists():
            self.log(component, "PASS", "Embedded Python exists")
        else:
            self.log(component, "FAIL", "Embedded Python missing")
    
    def run_all(self):
        """Run all validations."""
        print("=" * 60)
        print("  AGENTRIC AI - COMPONENT VALIDATION")
        print("=" * 60)
        
        self.validate_launch_bat()
        self.validate_launch_gpu_bat()
        self.validate_ui_package()
        self.validate_tools()
        self.validate_core_system()
        
        print("\n" + "=" * 60)
        print("  VALIDATION SUMMARY")
        print("=" * 60)
        print(f"  Passed:   {self.passed}")
        print(f"  Failed:   {self.failed}")
        print(f"  Warnings: {self.warnings}")
        print("=" * 60)
        
        if self.failed > 0:
            print("  STATUS: FAILED - Some components need attention")
            return False
        elif self.warnings > 0:
            print("  STATUS: PASSED WITH WARNINGS")
            return True
        else:
            print("  STATUS: ALL CHECKS PASSED")
            return True
    
    def save_report(self, output_path: str = None):
        """Save validation report to file."""
        if output_path is None:
            output_path = self.root / "Logs" / "validation_report.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings
            },
            "results": self.results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    validator = AgentricAIValidator()
    success = validator.run_all()
    validator.save_report()
    sys.exit(0 if success else 1)
