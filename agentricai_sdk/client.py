"""
AgentricAI Python SDK for easy integration and client usage.
"""
import httpx
from typing import AsyncIterator, Optional, Dict, List, Any
import json


class AgentricAIClient:
    """Python client for AgentricAI API."""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:3939",
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """Initialize AgentricAI client."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers=self._get_headers()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def chat(
        self,
        text: str,
        agent_id: str = "lacy",
        resource: str = "default",
        thread: str = "default",
        stream: bool = True
    ) -> AsyncIterator[str] | Dict[str, Any]:
        """Chat with an agent."""
        payload = {
            "text": text,
            "agent_id": agent_id,
            "resource": resource,
            "thread": thread,
            "stream": stream
        }
        
        if stream:
            async with self.client.stream(
                "POST",
                "/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if not data.get("done"):
                            yield data.get("chunk", "")
        else:
            response = await self.client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List available agents."""
        response = await self.client.get("/api/agents")
        response.raise_for_status()
        data = response.json()
        return data.get("agents", [])
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details."""
        response = await self.client.get(f"/api/agents/{agent_id}")
        response.raise_for_status()
        return response.json()
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        response = await self.client.get("/api/tools")
        response.raise_for_status()
        data = response.json()
        return data.get("tools", [])
    
    async def execute_tool(
        self,
        tool_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a tool."""
        payload = {
            "tool_id": tool_id,
            "parameters": parameters or {}
        }
        response = await self.client.post("/api/tools/execute", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_memory(
        self,
        resource: str,
        thread: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation memory."""
        response = await self.client.get(
            f"/api/memory/conversations/{resource}/{thread}",
            params={"limit": limit}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("messages", [])
    
    async def store_memory(
        self,
        key: str,
        value: Any,
        scope: str = "global",
        scope_id: str = "default"
    ) -> Dict[str, Any]:
        """Store a memory entry."""
        payload = {
            "key": key,
            "value": value,
            "scope": scope,
            "scope_id": scope_id
        }
        response = await self.client.post("/api/memory/store", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def retrieve_memory(
        self,
        key: str,
        scope: str = "global",
        scope_id: str = "default"
    ) -> Any:
        """Retrieve a memory entry."""
        payload = {
            "key": key,
            "scope": scope,
            "scope_id": scope_id
        }
        response = await self.client.post("/api/memory/retrieve", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("value")
    
    async def search_memory(
        self,
        query: str,
        scope: str = "global",
        scope_id: str = "default",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memory entries."""
        payload = {
            "query": query,
            "scope": scope,
            "scope_id": scope_id,
            "limit": limit
        }
        response = await self.client.post("/api/memory/search", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health status."""
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health check."""
        response = await self.client.get("/health/detailed")
        response.raise_for_status()
        return response.json()
    
    async def get_models(self) -> List[str]:
        """Get available models."""
        response = await self.client.get("/api/models")
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])
    
    async def get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information."""
        response = await self.client.get("/api/hardware")
        response.raise_for_status()
        return response.json()
    
    async def login(self, username: str, password: str) -> Dict[str, str]:
        """Authenticate user."""
        payload = {
            "username": username,
            "password": password
        }
        response = await self.client.post("/api/auth/login", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


# Synchronous wrapper for easier use
class AgentricAI:
    """Synchronous wrapper for AgentricAIClient."""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:3939",
        api_key: Optional[str] = None
    ):
        """Initialize sync client."""
        import asyncio
        self.client = AgentricAIClient(base_url, api_key)
        self.loop = asyncio.new_event_loop()
    
    def chat(
        self,
        text: str,
        agent_id: str = "lacy",
        resource: str = "default",
        thread: str = "default"
    ) -> str:
        """Chat with agent (blocking)."""
        async def _chat():
            responses = []
            async for chunk in await self.client.chat(
                text, agent_id, resource, thread, stream=True
            ):
                responses.append(chunk)
            return "".join(responses)
        
        return self.loop.run_until_complete(_chat())
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List agents (blocking)."""
        return self.loop.run_until_complete(self.client.list_agents())
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List tools (blocking)."""
        return self.loop.run_until_complete(self.client.list_tools())
    
    def get_memory(self, resource: str, thread: str) -> List[Dict[str, Any]]:
        """Get memory (blocking)."""
        return self.loop.run_until_complete(
            self.client.get_memory(resource, thread)
        )
    
    def close(self):
        """Close client."""
        self.loop.run_until_complete(self.client.close())
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
