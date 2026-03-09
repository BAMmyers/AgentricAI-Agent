"""
AgentricAI Launch Logger
Comprehensive logging system for tracking execution, packages, errors, and imports.
Generates detailed log.txt for debugging and auditing.
"""
import os
import sys
import time
import traceback
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set


class LaunchLogger:
    """Comprehensive launch logger for AgentricAI system."""
    
    def __init__(self, log_file: str = "log.txt", root_dir: str = None):
        self.root_dir = Path(root_dir or os.getcwd())
        self.log_file = self.root_dir / log_file
        self.start_time = time.time()
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.imports_success: Set[str] = set()
        self.imports_failed: Set[str] = set()
        self.packages_found: Dict[str, str] = {}
        self.packages_missing: Set[str] = set()
        self.modules_loaded: List[str] = []
        self.flags: List[Dict] = []
        self.execution_trace: List[str] = []
        
        # Initialize log file
        self._init_log_file()
        
    def _init_log_file(self):
        """Initialize the log file with header."""
        header = f"""
{'='*80}
AGENTRICAI LAUNCH LOG
{'='*80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Root Directory: {self.root_dir}
Python Version: {sys.version}
Python Executable: {sys.executable}
Platform: {sys.platform}
Working Directory: {os.getcwd()}
{'='*80}

"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(header)
    
    def log(self, message: str, level: str = "INFO", flag: str = None):
        """Log a message with optional flag."""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        elapsed = time.time() - self.start_time
        
        flag_str = f" [{flag}]" if flag else ""
        log_line = f"[{timestamp}] [+{elapsed:.3f}s]{flag_str} [{level}] {message}"
        
        self.execution_trace.append(log_line)
        self._append_log(log_line)
        
        if flag:
            self.flags.append({
                "timestamp": timestamp,
                "elapsed": elapsed,
                "flag": flag,
                "level": level,
                "message": message
            })
    
    def _append_log(self, line: str):
        """Append a line to the log file."""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    
    def flag_error(self, message: str, exception: Exception = None):
        """Flag an error."""
        error_info = {
            "message": message,
            "exception": str(exception) if exception else None,
            "traceback": traceback.format_exc() if exception else None,
            "timestamp": datetime.now().isoformat()
        }
        self.errors.append(error_info)
        self.log(message, level="ERROR", flag="ERROR")
        if exception:
            self.log(f"Exception: {exception}", level="ERROR", flag="ERROR_DETAIL")
            if error_info["traceback"]:
                for line in error_info["traceback"].split('\n'):
                    if line.strip():
                        self.log(f"  {line}", level="ERROR", flag="TRACEBACK")
    
    def flag_warning(self, message: str):
        """Flag a warning."""
        self.warnings.append({"message": message, "timestamp": datetime.now().isoformat()})
        self.log(message, level="WARNING", flag="WARNING")
    
    def flag_incomplete(self, component: str, reason: str):
        """Flag an incomplete component."""
        self.log(f"INCOMPLETE: {component} - {reason}", level="WARN", flag="INCOMPLETE")
    
    def flag_dropout(self, component: str, reason: str):
        """Flag a dropout (component that failed to load)."""
        self.log(f"DROPOUT: {component} - {reason}", level="ERROR", flag="DROPOUT")
    
    def track_import(self, module_name: str, success: bool, error: str = None):
        """Track an import attempt."""
        if success:
            self.imports_success.add(module_name)
            self.log(f"Import OK: {module_name}", level="DEBUG", flag="IMPORT_OK")
        else:
            self.imports_failed.add(module_name)
            self.flag_error(f"Import FAILED: {module_name} - {error}")
    
    def track_package(self, package_name: str, version: str = None, found: bool = True):
        """Track a package."""
        if found:
            self.packages_found[package_name] = version or "unknown"
            self.log(f"Package found: {package_name} ({version or 'version unknown'})", level="DEBUG", flag="PACKAGE")
        else:
            self.packages_missing.add(package_name)
            self.flag_warning(f"Package missing: {package_name}")
    
    def track_module_loaded(self, module_name: str):
        """Track a loaded module."""
        self.modules_loaded.append(module_name)
        self.log(f"Module loaded: {module_name}", level="DEBUG", flag="MODULE")
    
    def scan_packages(self):
        """Scan for installed packages."""
        self.log("Scanning installed packages...", level="INFO", flag="PACKAGE_SCAN")
        
        required_packages = [
            "fastapi", "uvicorn", "requests", "psutil", "gputil", 
            "pydantic", "python-multipart", "sqlite3", "json", "asyncio"
        ]
        
        for pkg in required_packages:
            try:
                if pkg == "sqlite3":
                    import sqlite3
                    self.track_package(pkg, "built-in", True)
                elif pkg == "json":
                    import json
                    self.track_package(pkg, "built-in", True)
                elif pkg == "asyncio":
                    import asyncio
                    self.track_package(pkg, "built-in", True)
                else:
                    try:
                        mod = __import__(pkg)
                        version = getattr(mod, '__version__', 'unknown')
                        self.track_package(pkg, version, True)
                    except ImportError:
                        self.track_package(pkg, None, False)
            except Exception as e:
                self.track_package(pkg, None, False)
    
    def scan_directory_structure(self):
        """Scan and log the directory structure."""
        self.log("Scanning directory structure...", level="INFO", flag="DIR_SCAN")
        
        key_dirs = ["core", "api", "UI", "Tools", "python_embedded"]
        for d in key_dirs:
            dir_path = self.root_dir / d
            if dir_path.exists():
                file_count = len(list(dir_path.rglob("*.*")))
                self.log(f"Directory OK: {d}/ ({file_count} files)", level="INFO", flag="DIR")
            else:
                self.flag_incomplete(f"Directory: {d}/", "Not found")
    
    def test_imports(self):
        """Test all critical imports."""
        self.log("Testing critical imports...", level="INFO", flag="IMPORT_TEST")
        
        critical_imports = [
            ("sys", "sys"),
            ("os", "os"),
            ("pathlib", "pathlib"),
            ("json", "json"),
            ("asyncio", "asyncio"),
            ("sqlite3", "sqlite3"),
            ("fastapi", "fastapi"),
            ("uvicorn", "uvicorn"),
            ("pydantic", "pydantic"),
            ("requests", "requests"),
            ("psutil", "psutil"),
        ]
        
        for name, module in critical_imports:
            try:
                __import__(module)
                self.track_import(name, True)
            except ImportError as e:
                self.track_import(name, False, str(e))
    
    def test_subsystems(self):
        """Test subsystem imports."""
        self.log("Testing subsystem imports...", level="INFO", flag="SUBSYSTEM_TEST")
        
        # Test core imports
        core_modules = [
            "core.agent_loader",
            "core.tool_loader", 
            "core.memory_router",
            "core.conversation_engine",
            "core.environment",
        ]
        
        for mod in core_modules:
            try:
                __import__(mod)
                self.track_import(mod, True)
            except Exception as e:
                self.track_import(mod, False, str(e))
        
        # Test API imports
        try:
            from api.main import init_api
            self.track_import("api.main", True)
        except Exception as e:
            self.track_import("api.main", False, str(e))
    
    def finalize(self) -> Dict[str, Any]:
        """Finalize the log and return summary."""
        elapsed = time.time() - self.start_time
        
        summary = f"""

{'='*80}
LAUNCH SUMMARY
{'='*80}
Total Execution Time: {elapsed:.3f} seconds

--- IMPORTS ---
Successful Imports: {len(self.imports_success)}
Failed Imports: {len(self.imports_failed)}
{f'Failed: {", ".join(self.imports_failed)}' if self.imports_failed else 'All imports successful'}

--- PACKAGES ---
Packages Found: {len(self.packages_found)}
Packages Missing: {len(self.packages_missing)}
{f'Missing: {", ".join(self.packages_missing)}' if self.packages_missing else 'All packages available'}

--- ERRORS ---
Total Errors: {len(self.errors)}
Total Warnings: {len(self.warnings)}

--- FLAGS ---
Total Flags: {len(self.flags)}
Error Flags: {len([f for f in self.flags if f['flag'] == 'ERROR'])}
Warning Flags: {len([f for f in self.flags if f['flag'] == 'WARNING'])}
Incomplete Flags: {len([f for f in self.flags if f['flag'] == 'INCOMPLETE'])}
Dropout Flags: {len([f for f in self.flags if f['flag'] == 'DROPOUT'])}

--- MODULES ---
Modules Loaded: {len(self.modules_loaded)}

{'='*80}
STATUS: {'FAILED' if self.errors else 'SUCCESS'}
{'='*80}
Log file saved to: {self.log_file}
"""
        
        self._append_log(summary)
        
        return {
            "success": len(self.errors) == 0,
            "elapsed": elapsed,
            "errors": self.errors,
            "warnings": self.warnings,
            "imports_success": list(self.imports_success),
            "imports_failed": list(self.imports_failed),
            "packages_found": self.packages_found,
            "packages_missing": list(self.packages_missing),
            "flags": self.flags,
            "log_file": str(self.log_file)
        }


def run_diagnostics(root_dir: str = None) -> Dict[str, Any]:
    """Run full diagnostics and return results."""
    logger = LaunchLogger(root_dir=root_dir)
    
    try:
        logger.log("Starting AgentricAI diagnostics...", level="INFO", flag="START")
        
        # Scan packages
        logger.scan_packages()
        
        # Scan directory structure
        logger.scan_directory_structure()
        
        # Test imports
        logger.test_imports()
        
        # Test subsystems
        logger.test_subsystems()
        
        logger.log("Diagnostics complete.", level="INFO", flag="COMPLETE")
        
    except Exception as e:
        logger.flag_error("Diagnostic failure", e)
    
    return logger.finalize()


if __name__ == "__main__":
    results = run_diagnostics()
    print(f"\nLog saved to: {results['log_file']}")
    print(f"Status: {'SUCCESS' if results['success'] else 'FAILED'}")
    if results['errors']:
        print(f"Errors: {len(results['errors'])}")
