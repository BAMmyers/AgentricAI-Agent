"""
AgentricAI - Agents as Services
Expose agents as HTTP services for external integration.
"""
import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn


class ServiceStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentService:
    """An agent exposed as a service."""
    id: str
    name: str
    description: str
    agent_id: str
    port: int
    host: str = "127.0.0.1"
    status: ServiceStatus = ServiceStatus.STOPPED
    endpoints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    requests_count: int = 0
    last_request: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentServiceManager:
    """Manages agents exposed as HTTP services."""
    
    def __init__(self):
        self.services: Dict[str, AgentService] = {}
        self.servers: Dict[str, uvicorn.Server] = {}
        self._next_port = 5000
        
        # Register default services
        self._register_default_services()
    
    def _register_default_services(self):
        """Register default agent services."""
        
        # Lacy Chat Service
        self.register_service(AgentService(
            id="lacy-chat",
            name="Lacy Chat Service",
            description="Direct chat interface to Lacy agent",
            agent_id="lacy",
            port=5001,
            endpoints=["/chat", "/stream", "/status"]
        ))
        
        # Code Generation Service
        self.register_service(AgentService(
            id="code-gen",
            name="Code Generation Service",
            description="Code generation and review service",
            agent_id="cody",
            port=5002,
            endpoints=["/generate", "/review", "/explain"]
        ))
        
        # Memory Service
        self.register_service(AgentService(
            id="memory-service",
            name="Memory Service",
            description="Agent memory management service",
            agent_id="lacy",
            port=5003,
            endpoints=["/store", "/retrieve", "/search", "/clear"]
        ))
        
        # Multi-Agent Orchestration Service
        self.register_service(AgentService(
            id="orchestrator",
            name="Orchestrator Service",
            description="Multi-agent task orchestration",
            agent_id="lacy",
            port=5004,
            endpoints=["/task", "/status", "/cancel"]
        ))
    
    def register_service(self, service: AgentService) -> bool:
        """Register a new agent service."""
        if service.id in self.services:
            return False
        
        self.services[service.id] = service
        return True
    
    def get_service(self, service_id: str) -> Optional[AgentService]:
        """Get a service by ID."""
        return self.services.get(service_id)
    
    def list_services(self) -> List[Dict]:
        """List all registered services."""
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "agent_id": s.agent_id,
                "port": s.port,
                "host": s.host,
                "status": s.status.value,
                "endpoints": s.endpoints,
                "requests_count": s.requests_count,
                "last_request": s.last_request.isoformat() if s.last_request else None
            }
            for s in self.services.values()
        ]
    
    def create_service_app(self, service: AgentService) -> FastAPI:
        """Create a FastAPI app for a service."""
        app = FastAPI(
            title=f"AgentricAI - {service.name}",
            description=service.description,
            version="1.0.0"
        )
        
        @app.get("/")
        async def root():
            return {
                "service": service.name,
                "agent_id": service.agent_id,
                "status": service.status.value
            }
        
        @app.get("/status")
        async def status():
            return {
                "service_id": service.id,
                "status": service.status.value,
                "requests_count": service.requests_count,
                "uptime": (datetime.now() - service.created_at).total_seconds()
            }
        
        # Chat endpoint (for chat services)
        if "/chat" in service.endpoints:
            @app.post("/chat")
            async def chat(request: Request):
                data = await request.json()
                message = data.get("message", "")
                
                service.requests_count += 1
                service.last_request = datetime.now()
                
                # Would integrate with actual agent
                return {
                    "response": f"[{service.agent_id}] Received: {message}",
                    "agent_id": service.agent_id
                }
        
        # Stream endpoint
        if "/stream" in service.endpoints:
            async def stream_response(message: str):
                for char in f"[{service.agent_id}] {message}":
                    yield f"data: {char}\n\n"
                    await asyncio.sleep(0.05)
            
            @app.post("/stream")
            async def stream(request: Request):
                data = await request.json()
                message = data.get("message", "")
                
                service.requests_count += 1
                service.last_request = datetime.now()
                
                return StreamingResponse(
                    stream_response(message),
                    media_type="text/event-stream"
                )
        
        # Generate endpoint (for code services)
        if "/generate" in service.endpoints:
            @app.post("/generate")
            async def generate(request: Request):
                data = await request.json()
                prompt = data.get("prompt", "")
                language = data.get("language", "python")
                
                service.requests_count += 1
                service.last_request = datetime.now()
                
                return {
                    "code": f"# Generated code for: {prompt}\n# Language: {language}\nprint('Hello, World!')",
                    "agent_id": service.agent_id
                }
        
        # Review endpoint
        if "/review" in service.endpoints:
            @app.post("/review")
            async def review(request: Request):
                data = await request.json()
                code = data.get("code", "")
                
                service.requests_count += 1
                service.last_request = datetime.now()
                
                return {
                    "review": f"Code review for {len(code)} characters",
                    "suggestions": ["Consider adding error handling", "Add documentation"],
                    "agent_id": service.agent_id
                }
        
        # Memory endpoints
        if "/store" in service.endpoints:
            @app.post("/store")
            async def store_memory(request: Request):
                data = await request.json()
                key = data.get("key")
                value = data.get("value")
                
                from core.memory_routing import get_memory_router, MemoryScope
                router = get_memory_router()
                router.store(key, value, MemoryScope.AGENT, service.agent_id)
                
                service.requests_count += 1
                service.last_request = datetime.now()
                
                return {"stored": True, "key": key}
        
        if "/retrieve" in service.endpoints:
            @app.post("/retrieve")
            async def retrieve_memory(request: Request):
                data = await request.json()
                key = data.get("key")
                
                from core.memory_routing import get_memory_router, MemoryScope
                router = get_memory_router()
                value = router.retrieve(key, MemoryScope.AGENT, service.agent_id)
                
                service.requests_count += 1
                service.last_request = datetime.now()
                
                return {"key": key, "value": value}
        
        # Task orchestration endpoints
        if "/task" in service.endpoints:
            @app.post("/task")
            async def create_task(request: Request):
                data = await request.json()
                task = data.get("task")
                agents = data.get("agents", [])
                
                service.requests_count += 1
                service.last_request = datetime.now()
                
                return {
                    "task_id": f"task-{datetime.now().timestamp()}",
                    "status": "created",
                    "agents": agents
                }
        
        return app
    
    async def start_service(self, service_id: str) -> bool:
        """Start an agent service."""
        service = self.get_service(service_id)
        if not service:
            return False
        
        if service.status == ServiceStatus.RUNNING:
            return True
        
        try:
            app = self.create_service_app(service)
            config = uvicorn.Config(
                app,
                host=service.host,
                port=service.port,
                log_level="error"
            )
            server = uvicorn.Server(config)
            
            # Run in background
            self.servers[service_id] = server
            service.status = ServiceStatus.RUNNING
            
            # Start server
            asyncio.create_task(server.serve())
            
            return True
        except Exception as e:
            service.status = ServiceStatus.ERROR
            service.metadata["error"] = str(e)
            return False
    
    def stop_service(self, service_id: str) -> bool:
        """Stop an agent service."""
        service = self.get_service(service_id)
        if not service:
            return False
        
        if service.status != ServiceStatus.RUNNING:
            return True
        
        try:
            if service_id in self.servers:
                self.servers[service_id].should_exit = True
                del self.servers[service_id]
            
            service.status = ServiceStatus.STOPPED
            return True
        except Exception as e:
            service.metadata["error"] = str(e)
            return False
    
    def get_service_url(self, service_id: str) -> Optional[str]:
        """Get the URL for a service."""
        service = self.get_service(service_id)
        if service:
            return f"http://{service.host}:{service.port}"
        return None
    
    def create_custom_service(
        self,
        name: str,
        agent_id: str,
        description: str = "",
        endpoints: List[str] = None,
        port: int = None
    ) -> AgentService:
        """Create a custom agent service."""
        service_id = f"custom-{name.lower().replace(' ', '-')}"
        
        if port is None:
            port = self._next_port
            self._next_port += 1
        
        service = AgentService(
            id=service_id,
            name=name,
            description=description,
            agent_id=agent_id,
            port=port,
            endpoints=endpoints or ["/chat", "/status"]
        )
        
        self.register_service(service)
        return service


# Global service manager
_service_manager = None

def get_service_manager() -> AgentServiceManager:
    """Get the global service manager."""
    global _service_manager
    if _service_manager is None:
        _service_manager = AgentServiceManager()
    return _service_manager
