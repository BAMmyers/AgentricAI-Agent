"""
AgentricAI - UI Launcher
Starts the Next.js UI with loading screen and backend services.
ChatGPT-style loading experience.
"""
import subprocess
import sys
import time
import os
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))


def check_ollama():
    """Check if Ollama is running."""
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        return True
    except:
        return False


def start_ollama():
    """Start Ollama in background."""
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )
    for i in range(30):
        time.sleep(1)
        if check_ollama():
            return True
    return False


def start_api_server():
    """Start the Python API server in background."""
    python_exe = str(ROOT_DIR / "python_embedded" / "python.exe")
    api_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "api.gateway:app", "--host", "127.0.0.1", "--port", "3939"],
        cwd=str(ROOT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return api_process


def check_npm():
    """Check if npm is available."""
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, shell=True)
        return result.returncode == 0
    except:
        return False


def start_ui():
    """Start the Next.js UI."""
    ui_dir = ROOT_DIR / "UI"
    
    # Check if node_modules exists
    node_modules = ui_dir / "node_modules"
    if not node_modules.exists():
        print("  Installing UI dependencies (first run)...")
        subprocess.run(["npm", "install"], cwd=str(ui_dir), shell=True, capture_output=True)
    
    # Start Next.js
    ui_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(ui_dir),
        shell=True
    )
    return ui_process


def main():
    print()
    print("  ============================================================")
    print("  |                                                          |")
    print("  |     AgentricAI - Sovereign Intelligence Platform          |")
    print("  |                                                          |")
    print("  ============================================================")
    print()
    
    # Check npm first
    if not check_npm():
        print("  ERROR: npm not found. Please install Node.js first.")
        print("         Download from: https://nodejs.org/")
        input("  Press Enter to exit...")
        return
    
    print("  Loading components...")
    print()
    
    # Step 1: Check/Start Ollama
    print("  [1/4] Checking Ollama...")
    if check_ollama():
        print("        Ollama: running")
    else:
        print("        Starting Ollama...")
        if start_ollama():
            print("        Ollama: started")
        else:
            print("        Ollama: unavailable (continuing)")
    
    # Step 2: Start API Server
    print("  [2/4] Starting API Server...")
    api_process = start_api_server()
    time.sleep(2)
    print("        API: http://127.0.0.1:3939")
    
    # Step 3: Start UI
    print("  [3/4] Launching UI...")
    ui_process = start_ui()
    
    # Wait for UI to start
    for i in range(15):
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:3000", timeout=1)
            break
        except Exception:
            pass
    
    # Step 4: Open browser
    print("  [4/4] Opening browser...")
    webbrowser.open("http://localhost:3000")
    
    print()
    print("  ============================================================")
    print("  |  AgentricAI is running!                                  |")
    print("  |                                                          |")
    print("  |  UI:  http://localhost:3000                              |")
    print("  |  API: http://127.0.0.1:3939                              |")
    print("  |                                                          |")
    print("  |  Press Ctrl+C to stop                                    |")
    print("  ============================================================")
    print()
    
    # Keep running
    try:
        ui_process.wait()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        ui_process.terminate()
        api_process.terminate()


if __name__ == "__main__":
    main()
