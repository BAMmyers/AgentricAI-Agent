"""
AgentricAI Pydantic Schemas.
Request and response models for API validation.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatRequest(BaseModel):
    """Chat request model."""
    text: str = Field(..., min_length=1, max_length=10000, description="User message")
    agent_id: str = Field(default="lacy", description="Agent to use")
    resource: str = Field(default="default", description="Resource identifier")
    thread: str = Field(default="default", description="Thread identifier")
    stream: bool = Field(default=True, description="Whether to stream response")
    
    @validator('text')
    def validate_text(cls, v):
        """Validate message text."""
        if not v or not v.strip():
            raise ValueError('Message text cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Agent response")
    agent_id: str = Field(..., description="Agent that responded")
    model: str = Field(..., description="Model used")
    timestamp: datetime = Field(default_factory=datetime.now)
    resource: str = Field(default="default")
    thread: str = Field(default="default")


class AgentInfo(BaseModel):
    """Agent information model."""
    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    model: Optional[str] = Field(None, description="Model used by agent")
    version: str = Field(default="1.0.0", description="Agent version")
    memory_scope: Optional[str] = Field(None, description="Memory scope")
    validated: bool = Field(default=True, description="Whether agent passed validation")


class AgentListResponse(BaseModel):
    """List of agents response."""
    agents: List[AgentInfo]
    count: int


class ToolInfo(BaseModel):
    """Tool information model."""
    id: str
    name: str
    category: str
    execution_mode: str
    validated: bool
    version: str = "1.0.0"


class ToolListResponse(BaseModel):
    """List of tools response."""
    tools: List[ToolInfo]
    count: int
    validated_count: int


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""
    tool_id: str = Field(..., description="Tool to execute")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Tool parameters")


class ToolExecuteResponse(BaseModel):
    """Tool execution response."""
    tool_id: str
    stdout: str
    stderr: str
    returncode: int
    success: bool


class MemoryEntryModel(BaseModel):
    """Memory entry model."""
    id: str
    key: str
    value: Any
    scope: str
    scope_id: str
    type: str
    created_at: datetime
    updated_at: datetime


class MemoryStoreRequest(BaseModel):
    """Memory store request."""
    key: str = Field(..., min_length=1, max_length=255)
    value: Any
    scope: str = Field(default="global")
    scope_id: str = Field(default="default")


class MemorySearchRequest(BaseModel):
    """Memory search request."""
    query: str = Field(..., min_length=1)
    scope: str = Field(default="global")
    scope_id: str = Field(default="default")
    limit: int = Field(default=10, ge=1, le=100)


class ConversationMessage(BaseModel):
    """Conversation message model."""
    id: int
    role: MessageRole
    content: str
    timestamp: datetime


class ConversationHistoryResponse(BaseModel):
    """Conversation history response."""
    resource: str
    thread: str
    messages: List[ConversationMessage]
    count: int


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    components: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class StreamChunk(BaseModel):
    """Streaming response chunk."""
    chunk: str
    done: bool = False
    agent_id: Optional[str] = None
