"""
Health check utilities for AgentricAI components.
"""
import asyncio
from datetime import datetime
from typing import Dict

class HealthCheck:
    def __init__(self):
        self.checks = {}

    def register(self, name: str, check_fn):
        self.checks[name] = check_fn

    async def run_all(self) -> Dict:
        results = {}
        for name, check_fn in self.checks.items():
            try:
                status = await asyncio.wait_for(check_fn(), timeout=5.0)
                results[name] = {
                    "status": "ok" if status else "failed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            except asyncio.TimeoutError:
                results[name] = {"status": "timeout"}
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
        return results

# Default health check instance
health = HealthCheck()

# example checks
async def check_ollama():
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=2) as resp:
                return resp.status == 200
    except Exception:
        return False


# To be registered by API initialization
