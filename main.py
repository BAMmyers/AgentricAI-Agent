"""
AgentricAI - Main Orchestrator
Entry point for the complete AgentricAI system.
Orchestrates all subsystems: Core, API, UI, Tools.
"""
import os
import sys
import asyncio
import subprocess
import threading
from pathlib import Path

# Add root to path
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# Import logger first
from launch_logger import LaunchLogger

# Initialize logger
logger = LaunchLogger(root_dir=str(ROOT_DIR))

# Import subsystems with logging
try:
    logger.log("Importing core subsystems...", level="INFO", flag="IMPORT")
    from core.main import CoreSystem
    logger.track_import("core.main", True)
except Exception as e:
    logger.track_import("core.main", False, str(e))
    logger.flag_error("Failed to import CoreSystem", e)

try:
    from api.main import init_api
    logger.track_import("api.main", True)
except Exception as e:
    logger.track_import("api.main", False, str(e))
    logger.flag_error("Failed to import init_api", e)


class AgentricAIOrchestrator:
    """Main orchestrator for the AgentricAI system."""
    
    def __init__(self):
        self.root_dir = ROOT_DIR
        self.core_system = None
        self.api_server = None
        self.running = False
        logger.log("Orchestrator initialized", level="INFO", flag="INIT")
        
    def check_ollama(self):
        """Check if Ollama is running, start if not."""
        import urllib.request
        import urllib.error
        
        logger.log("Checking Ollama service...", level="INFO", flag="OLLAMA")
        
        try:
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            logger.log("Ollama is running", level="INFO", flag="OLLAMA_OK")
            print("[AgentricAI] Ollama is running")
            return True
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            logger.log("Ollama not running, attempting to start...", level="WARN", flag="OLLAMA_START")
            print("[AgentricAI] Starting Ollama...")
            try:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True
                )
                logger.log("Ollama start command issued", level="INFO", flag="OLLAMA_START")
            except Exception as e:
                logger.flag_error("Failed to start Ollama", e)
            return False
    
    def init_subsystems(self):
        """Initialize all subsystems."""
        logger.log("Initializing subsystems...", level="INFO", flag="SUBSYSTEM")
        print("[AgentricAI] Initializing subsystems...")
        
        # Initialize core system
        logger.log("Loading Core System...", level="INFO", flag="CORE")
        print("[AgentricAI] Loading Core System...")
        try:
            self.core_system = CoreSystem()
            logger.log("Core System loaded successfully", level="INFO", flag="CORE_OK")
        except Exception as e:
            logger.flag_error("Failed to load Core System", e)
            logger.flag_incomplete("CoreSystem", str(e))
            return
        
        # Initialize API
        logger.log("Loading API Gateway...", level="INFO", flag="API")
        print("[AgentricAI] Loading API Gateway...")
        try:
            self.api_server = init_api(self.core_system)
            logger.log("API Gateway loaded successfully", level="INFO", flag="API_OK")
        except Exception as e:
            logger.flag_error("Failed to load API Gateway", e)
            logger.flag_incomplete("API Gateway", str(e))
            return
        
        logger.log("All subsystems initialized", level="INFO", flag="SUBSYSTEM_OK")
        print("[AgentricAI] All subsystems initialized")
        
    def run(self, host="127.0.0.1", port=3939):
        """Run the complete AgentricAI system."""
        logger.log(f"Starting AgentricAI on {host}:{port}", level="INFO", flag="START")
        print("=" * 60)
        print("  AGENTRIC AI - SOVEREIGN INTELLIGENCE PLATFORM")
        print("=" * 60)
        
        # Check Ollama
        self.check_ollama()
        
        # Initialize subsystems
        self.init_subsystems()
        
        self.running = True
        
        # Start API server (blocking)
        logger.log(f"Starting API server on http://{host}:{port}", level="INFO", flag="SERVER")
        print(f"[AgentricAI] Starting API server on http://{host}:{port}")
        print("[AgentricAI] Press Ctrl+C to stop")
        print("-" * 60)
        
        try:
            import uvicorn
            uvicorn.run(
                self.api_server,
                host=host,
                port=port,
                log_level="info"
            )
        except Exception as e:
            logger.flag_error("Server failed to start", e)
            raise


def main():
    """Main entry point."""
    try:
        # Run package scan
        logger.scan_packages()
        
        # Run diagnostics
        logger.test_imports()
        
        # Start orchestrator
        orchestrator = AgentricAIOrchestrator()
        orchestrator.run()
        
    except KeyboardInterrupt:
        logger.log("Shutdown requested by user", level="INFO", flag="SHUTDOWN")
        print("\n[AgentricAI] Shutting down...")
    except Exception as e:
        logger.flag_error("Fatal error in main", e)
        raise
    finally:
        # Finalize log
        results = logger.finalize()
        print(f"\n[AgentricAI] Log saved to: {results['log_file']}")


if __name__ == "__main__":
    main()
