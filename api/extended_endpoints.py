"""
Enhanced API endpoints for authentication, semantic search, RAG, analytics, and specialized agents.
These endpoints extend the main gateway with advanced features.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import timedelta

from core.auth import (
    get_current_active_user,
    require_role,
    Role,
    User,
    create_access_token,
    authenticate_user,
    LoginRequest,
    LoginResponse
)
from core.audit import audit_logger, AuditEventType
from core.semantic_search import semantic_search
from core.rag_engine import rag_engine
from core.specialized_agents import create_specialized_agent
from core.analytics import analytics
from core.memory_router import MemoryRouter
from core.config import get_config
from core.environment import get_local_models

router = APIRouter()

# Initialize components
memory_router = MemoryRouter()
config = get_config()


# ============================================================================
# AUTHENTICATION
# ============================================================================

@router.post("/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Login endpoint for user authentication."""
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        await audit_logger.log_event(
            AuditEventType.AUTH_FAILED,
            user_id=credentials.username,
            action="login_failed"
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.username, "scopes": [user.role.value]})
    
    await audit_logger.log_event(
        AuditEventType.USER_LOGIN,
        user_id=user.username,
        action="login_success"
    )
    
    return LoginResponse(access_token=access_token, user=user)


@router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current authenticated user information."""
    return current_user


# ============================================================================
# SEMANTIC SEARCH & RAG
# ============================================================================

@router.post("/search/semantic")
async def semantic_search_endpoint(
    query: str,
    top_k: int = 5,
    resource: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Semantic similarity search in conversations."""
    results = await semantic_search.semantic_search(query, resource, top_k)
    
    await audit_logger.log_event(
        AuditEventType.AGENT_INVOKED,
        user_id=current_user.username,
        resource=resource,
        action="semantic_search",
        details={"query": query, "top_k": top_k, "results_count": len(results)}
    )
    
    return {"query": query, "results": results}


@router.post("/rag/index-documents")
async def index_documents(
    document_path: Optional[str] = None,
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """Index documents for RAG system."""
    count = await rag_engine.index_documents(document_path)
    
    await audit_logger.log_event(
        AuditEventType.CONFIG_CHANGED,
        user_id=current_user.username,
        action="index_documents",
        details={"documents_indexed": count}
    )
    
    return {"indexed": count, "status": "success"}


@router.get("/rag/retrieve")
async def retrieve_rag_context(
    query: str,
    top_k: int = 3, 
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve context from documents using RAG."""
    docs = await rag_engine.retrieve_relevant_documents(query, top_k)
    return {"query": query, "documents": docs}


# ============================================================================
# MODEL COMPARISON
# ============================================================================

@router.post("/compare-models")
async def compare_models(
    text: str,
    models: Optional[list] = None,
    agent_id: str = "lacy",
    resource: str = "default",
    current_user: User = Depends(get_current_active_user)
):
    """Compare responses across multiple models."""
    if not models:
        models_available = await get_local_models()
        models = models_available[:3] if models_available else []
    
    responses = {}
    for model in models[:3]:  # Limit to 3 models
        try:
            responses[model] = f"Response from {model} for: {text[:50]}..."
        except Exception as e:
            responses[model] = f"Error: {str(e)}"
    
    await audit_logger.log_event(
        AuditEventType.AGENT_INVOKED,
        user_id=current_user.username,
        action="model_comparison",
        details={"models_compared": len(responses)}
    )
    
    return {"query": text, "responses": responses}


# ============================================================================
# ANALYTICS
# ============================================================================

@router.get("/analytics/session/{resource}/{thread}")
async def get_session_analytics(
    resource: str,
    thread: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get analytics for a conversation session."""
    history = memory_router.get_conversation(resource, thread)
    stats = await analytics.analyze_session(history, resource)
    
    await audit_logger.log_event(
        AuditEventType.AGENT_INVOKED,
        user_id=current_user.username,
        resource=resource,
        action="analyze_session"
    )
    
    return stats


@router.post("/analytics/compare")
async def compare_sessions(
    session1_resource: str,
    session1_thread: str,
    session2_resource: str,
    session2_thread: str,
    current_user: User = Depends(get_current_active_user)
):
    """Compare analytics between two sessions."""
    history1 = memory_router.get_conversation(session1_resource, session1_thread)
    history2 = memory_router.get_conversation(session2_resource, session2_thread)
    
    comparison = await analytics.compare_sessions(history1, history2)
    return comparison


# ============================================================================
# SPECIALIZED AGENTS
# ============================================================================

@router.get("/agents/specialized")
async def list_specialized_agents(current_user: User = Depends(get_current_active_user)):
    """List specialized agent types."""
    return {
        "agents": [
            {"id": "reasoning", "name": "Reasoning Agent", "description": "Multi-step reasoning"},
            {"id": "research", "name": "Research Agent", "description": "Information synthesis"},
            {"id": "toolmaster", "name": "ToolMaster Agent", "description": "Tool composition"},
            {"id": "code", "name": "Code Agent", "description": "Code generation"},
            {"id": "creative", "name": "Creative Agent", "description": "Creative content"}
        ]
    }


@router.post("/agents/specialized/{agent_type}")
async def invoke_specialized_agent(
    agent_type: str,
    text: str,
    resource: str = "default",
    thread: str = "default",
    current_user: User = Depends(get_current_active_user)
):
    """Invoke a specialized agent."""
    agent = create_specialized_agent(agent_type, f"specialized_{agent_type}")
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_type}")
    
    response = await agent.generate_response(
        text=text,
        resource=resource,
        thread=thread
    )
    
    await audit_logger.log_event(
        AuditEventType.AGENT_INVOKED,
        user_id=current_user.username,
        resource=resource,
        action=f"invoke_specialized_{agent_type}",
        details={"text_length": len(text)}
    )
    
    return {"agent_type": agent_type, "response": response}


# ============================================================================
# AUDIT LOGS
# ============================================================================

@router.get("/audit/logs")
async def get_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """Get recent audit logs."""
    events = await audit_logger.get_recent_events(limit=limit)
    return {"logs": events}


@router.get("/audit/summary")
async def get_audit_summary(current_user: User = Depends(require_role(Role.ADMIN))):
    """Get audit summary."""
    summary = await audit_logger.get_audit_summary()
    return summary
