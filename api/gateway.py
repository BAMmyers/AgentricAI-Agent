"""
AgentricAI API Gateway
FastAPI endpoints for the complete AgentricAI system with proper validation and streaming.
"""
from fastapi import FastAPI, Request, HTTPException, Depends, WebSocket, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.exceptions import RequestValidationError
import asyncio
import json
from datetime import datetime
from typing import Optional
import signal
import sys

# New imports for observability and background tasks
from core.metrics import metrics_middleware, metrics_endpoint, agent_invocations
from core.tracing import init_tracing, get_tracer
from core.health import health, check_ollama
from core.config import get_config
from core.tasks import process_long_running_agent_task

# Ensure Celery app imported for worker
from core.tasks import celery_app

# New feature imports
from core.auth import get_current_active_user, require_role, Role, create_access_token, authenticate_user, LoginRequest, LoginResponse, User
from core.audit import audit_logger, AuditEventType
from core.semantic_search import semantic_search
from core.rag_engine import rag_engine
from core.specialized_agents import create_specialized_agent
from core.analytics import analytics

# Extended API endpoints
from api.extended_endpoints import router as extended_router

# Core imports
from core.agent_loader import AgentLoader
from core.conversation_engine import ConversationEngine
from core.environment import get_local_models, get_gpu_info, get_cpu_info, get_ram_info
from core.memory_router import MemoryRouter, MemoryScope, MemoryType
from core.tool_loader import ToolLoader
from core.config import get_config
from core.schemas import (
    ChatRequest, ChatResponse, AgentInfo, AgentListResponse,
    ToolInfo, ToolListResponse, ToolExecuteRequest, ToolExecuteResponse,
    HealthCheckResponse, ErrorResponse
)
from core.logging_config import get_logger, init_logging

# Initialize logging
init_logging()
logger = get_logger(__name__)

# Load configuration
config = get_config()

# Create FastAPI app early so middleware can be added
app = FastAPI(
    title="AgentricAI API",
    version="1.0.0",
    description="Sovereign Intelligence Platform - Local-first AI agent ecosystem"
)

# Apply GZIP middleware if enabled
if config.enable_gzip:
    app.add_middleware(GZIPMiddleware, minimum_size=config.gzip_minimum_size)

# Add metrics middleware
app.middleware('http')(metrics_middleware)

# Initialize tracing
init_tracing(app)

# Register health checks
health.register('ollama', check_ollama)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for graceful shutdown
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    _shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Initialize core systems
logger.info("Initializing AgentricAI core systems...")
agent_loader = AgentLoader()
tool_loader = ToolLoader()
memory_router = MemoryRouter()
conversation_engine = ConversationEngine(agent_loader, tool_loader, memory_router)
logger.info(f"Loaded {len(agent_loader.agents)} agents, {len(tool_loader.tools)} tools")

# Register extended endpoints
app.include_router(extended_router, prefix="/api", tags=["advanced"])


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc.errors())
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc)
        ).model_dump()
    )


async def sse_stream(generator):
    """
    Convert async generator to SSE stream with proper formatting.
    
    Format:
    data: {"chunk": "text", "done": false}
    data: {"chunk": "", "done": true}
    """
    try:
        async for chunk in generator:
            # Format as SSE data
            data = json.dumps({"chunk": chunk, "done": False})
            yield f"data: {data}\n\n"
        
        # Send completion signal
        done_data = json.dumps({"chunk": "", "done": True})
        yield f"data: {done_data}\n\n"
    
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_data = json.dumps({"error": str(e), "done": True})
        yield f"data: {error_data}\n\n"


# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        components={
            "agents": "ok" if agent_loader.agents else "warning",
            "tools": "ok" if tool_loader.tools else "warning",
            "memory": "ok"
        }
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system information."""
    agents_validation = agent_loader.get_validation_report()
    tools_validation = tool_loader.get_validation_report()
    
    return {
        "status": "healthy" if agents_validation["valid_agents"] > 0 else "degraded",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "uptime": "running",
    }

# Prometheus metrics endpoint
@app.get("/metrics")
async def prometheus_metrics():
    return await metrics_endpoint()

# Kubernetes probes
@app.get("/healthz")
async def liveness():
    return {"status": "alive"}

@app.get("/readyz")
async def readiness():
    results = await health.run_all()
    all_ok = all(r.get("status") == "ok" for r in results.values())
    return {"ready": all_ok, "checks": results}


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================

@app.post("/api/chat")
async def chat(request: Request):
    """
    Chat with an agent.
    
    Request body:
    - text: User message (required)
    - agent_id: Agent to use (default: "lacy")
    - resource: Resource identifier (default: "default")
    - thread: Thread identifier (default: "default")
    - stream: Whether to stream response (default: true)
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # Validate request
    text = data.get("text")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Missing or empty 'text' field")
    
    # sanitize input and detect injections
    from core.security import InputValidator
    try:
        text = InputValidator.sanitize_text(text)
        if InputValidator.detect_prompt_injection(text):
            logger.warning(f"Potential prompt injection: {text}")
            raise HTTPException(status_code=400, detail="Invalid request content")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    agent_id = data.get("agent_id", "lacy")
    resource = data.get("resource", "default")
    thread = data.get("thread", "default")
    stream = data.get("stream", True)
    
    # Get agent
    try:
        agent = agent_loader.get_agent(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Get memory context
    memory_context = memory_router.read_memory(resource, thread)
    
    # start tracing and metrics
    tracer = get_tracer("api.chat")
    span = tracer.start_span("process_chat")
    span.set_attribute("agent_id", agent_id)
    span.set_attribute("resource", resource)
    span.set_attribute("thread", thread)
    
    agent_invocations.labels(agent_id=agent_id, status="started").inc()
    
    try:
        if stream:
            # Stream response
            generator = conversation_engine.stream_response(
                agent_id=agent_id,
                text=text,
                resource=resource,
                thread=thread,
                memory_context=memory_context
            )
            result = StreamingResponse(
                sse_stream(generator),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Non-streaming response
            response = await conversation_engine.generate_response(
                agent_id=agent_id,
                text=text,
                resource=resource,
                thread=thread,
                memory_context=memory_context
            )
            result = ChatResponse(
                response=response,
                agent_id=agent_id,
                model=getattr(agent, 'model', config.default_model),
                resource=resource,
                thread=thread
            ).model_dump()
        # success
        agent_invocations.labels(agent_id=agent_id, status="success").inc()
        return result
    except Exception as e:
        agent_invocations.labels(agent_id=agent_id, status="error").inc()
        span.record_exception(e)
        span.set_status("error")
        raise
    finally:
        span.end()


# ============================================================================
# AGENT ENDPOINTS
# ============================================================================

@app.get("/api/agents", response_model=AgentListResponse)
async def get_agents():
    """List all available agents."""
    agents = agent_loader.list_agents()
    return AgentListResponse(
        agents=[AgentInfo(**a) for a in agents],
        count=len(agents)
    )


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get a specific agent's information."""
    try:
        agent = agent_loader.get_agent(agent_id)
        return {
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "model": getattr(agent, "model", None),
                "version": getattr(agent, "version", "1.0.0"),
                "memory_config": getattr(agent, "memory_config", {}),
                "metadata": agent.get_metadata() if hasattr(agent, 'get_metadata') else {}
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/agents/create")
async def create_agent(request: Request):
    """Create a new agent from configuration."""
    data = await request.json()
    try:
        agent_id = agent_loader.create_agent(data)
        return {"agent_id": agent_id, "status": "created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent."""
    try:
        agent_loader.delete_agent(agent_id)
        return {"status": "deleted", "agent_id": agent_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# TOOL ENDPOINTS
# ============================================================================

@app.get("/api/tools", response_model=ToolListResponse)
async def get_tools():
    """List all available tools."""
    tools = tool_loader.list_tools()
    validated = [t for t in tools if t.get("validated")]
    return ToolListResponse(
        tools=[ToolInfo(
            id=t["id"],
            name=t.get("name", t["id"]),
            category=t.get("category", "general"),
            execution_mode=t.get("execution_mode", "CPU"),
            validated=t.get("validated", False),
            version=t.get("version", "1.0.0")
        ) for t in tools],
        count=len(tools),
        validated_count=len(validated)
    )


@app.get("/api/tools/validation")
async def get_tools_validation():
    """Get tool validation report."""
    return tool_loader.get_validation_report()


@app.post("/api/tools/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: Request):
    """Execute a tool with parameters."""
    data = await request.json()
    tool_id = data.get("tool_id")
    parameters = data.get("parameters", {})
    
    if not tool_id:
        raise HTTPException(status_code=400, detail="Missing 'tool_id'")
    
    try:
        result = tool_loader.execute_tool(tool_id, parameters)
        return ToolExecuteResponse(
            tool_id=tool_id,
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            returncode=result.get("returncode", -1),
            success=result.get("success", False)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# MEMORY ENDPOINTS
# ============================================================================

@app.get("/api/memory/conversations/{resource}/{thread}")
async def get_conversation(resource: str, thread: str, limit: int = 50):
    """Get conversation history for a resource/thread."""
    history = memory_router.get_conversation(resource, thread, limit)
    return {
        "resource": resource,
        "thread": thread,
        "messages": history,
        "count": len(history)
    }


@app.delete("/api/memory/conversations/{resource}/{thread}")
async def clear_conversation(resource: str, thread: str):
    """Clear conversation history."""
    memory_router.clear_conversation(resource, thread)
    return {"status": "cleared", "resource": resource, "thread": thread}


@app.post("/api/tasks/async")
async def submit_async_task(request: Request):
    """Submit long-running task to background queue."""
    data = await request.json()
    agent_id = data.get("agent_id")
    text = data.get("text")
    resource = data.get("resource","default")
    if not agent_id or not text:
        raise HTTPException(status_code=400, detail="agent_id and text required")
    task = process_long_running_agent_task.delay(agent_id, text, resource)
    return {"task_id": task.id, "status": "queued"}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    from celery.result import AsyncResult
    res = AsyncResult(task_id)
    return {"status": res.status, "result": res.result if res.ready() else None}

@app.post("/api/memory/store")
async def store_memory(request: Request):
    """Store a memory entry."""
    data = await request.json()
    
    key = data.get("key")
    value = data.get("value")
    scope = data.get("scope", "global")
    scope_id = data.get("scope_id", "default")
    
    if not key:
        raise HTTPException(status_code=400, detail="Missing 'key'")
    
    entry = memory_router.store(
        key=key,
        value=value,
        scope=MemoryScope(scope),
        scope_id=scope_id
    )
    return {"success": True, "entry": entry.to_dict()}


@app.post("/api/memory/retrieve")
async def retrieve_memory(request: Request):
    """Retrieve a memory entry."""
    data = await request.json()
    
    key = data.get("key")
    scope = data.get("scope", "global")
    scope_id = data.get("scope_id", "default")
    
    if not key:
        raise HTTPException(status_code=400, detail="Missing 'key'")
    
    value = memory_router.retrieve(key, MemoryScope(scope), scope_id)
    return {"key": key, "value": value}


@app.post("/api/memory/search")
async def search_memory(request: Request):
    """Search memory entries."""
    data = await request.json()
    
    query = data.get("query", "")
    scope = data.get("scope", "global")
    scope_id = data.get("scope_id", "default")
    limit = data.get("limit", 10)
    
    results = memory_router.search(query, MemoryScope(scope), scope_id, limit)
    return {"results": results, "count": len(results)}


# ============================================================================
# MODEL ENDPOINTS
# ============================================================================

@app.get("/api/models")
async def get_models():
    """Get available local models from Ollama."""
    return {"models": get_local_models()}


# ============================================================================
# HARDWARE ENDPOINTS
# ============================================================================

@app.get("/api/hardware")
async def get_hardware():
    """Get hardware information."""
    return {
        "gpu": get_gpu_info(),
        "cpu": get_cpu_info(),
        "ram": get_ram_info()
    }


# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AgentricAI",
        "version": "1.0.0",
        "description": "Sovereign Intelligence Platform - Local-first AI agent ecosystem",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "agents": "/api/agents",
            "tools": "/api/tools",
            "memory": "/api/memory",
            "models": "/api/models",
            "hardware": "/api/hardware",
            "health": "/health"
        },
        "stats": {
            "agents": len(agent_loader.agents),
            "tools": len(tool_loader.tools)
        }
    }


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info(f"AgentricAI API started on {config.api_url}")
    logger.info(f"Ollama URL: {config.ollama_url}")
    logger.info(f"Default model: {config.default_model}")


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown handler."""
    logger.info("AgentricAI API shutting down...")


def run_server():
    """Run the API server."""
    import uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.api_port,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    run_server()
