@echo off
setlocal enabledelayedexpansion

cd /d "C:\Program Files\AgentricAI"

echo.
echo   ============================================================
echo   ^|                                                        ^|
echo   ^|     AgentricAI - Sovereign Intelligence Platform        ^|
echo   ^|                                                        ^|
echo   ============================================================
echo.
echo   Loading components...
echo.

REM Step 1: Check Ollama
echo   [1/4] Checking Ollama...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo        Starting Ollama...
    start "Ollama-AgentricAI" cmd /c "ollama serve"
    timeout /t 5 /nobreak >nul
) else (
    echo        Ollama is running
)

REM Step 2: Start API Server
echo   [2/4] Starting API Server...
start "AgentricAI-API" cmd /c "cd /d C:\Program Files\AgentricAI && .\python_embedded\python.exe -m uvicorn api.gateway:app --host 127.0.0.1 --port 3939"
timeout /t 3 /nobreak >nul
echo        API: http://127.0.0.1:3939

REM Step 3: Launch UI (Next.js)
echo   [3/4] Launching UI...
start "AgentricAI-UI" cmd /c "cd /d C:\Program Files\AgentricAI\Docs\agentricai-ui && npm run dev"
timeout /t 8 /nobreak >nul
echo        UI: http://localhost:3000

REM Step 4: Open browser
echo   [4/4] Opening browser...
start http://localhost:3000

echo.
echo   ============================================================
echo   ^|                                                        ^|
echo   ^|  AgentricAI is running!                                ^|
echo   ^|                                                        ^|
echo   ^|  UI:  http://localhost:3000                            ^|
echo   ^|  API: http://127.0.0.1:3939                            ^|
echo   ^|                                                        ^|
echo   ^|  Close this window to stop all services                ^|
echo   ============================================================
echo.
echo   Press any key to stop all services...
pause >nul

REM Cleanup
taskkill /FI "WINDOWTITLE eq Ollama-AgentricAI*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AgentricAI-API*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AgentricAI-UI*" /F >nul 2>&1
echo   Services stopped.
