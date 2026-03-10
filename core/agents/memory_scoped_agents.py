"""
Memory-scoped agents for AgentricAI.
Provides resource-scoped and thread-scoped memory agents with Ollama integration.
"""
import json
import urllib.request
import urllib.error
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import uuid


OLLAMA_URL = "http://localhost:11434"


async def call_ollama_async(model: str, prompt: str) -> str:
    """
    Call Ollama API for text generation (non-streaming).
    
    Args:
        model: The model name to use (e.g., 'lacy:latest')
        prompt: The prompt to send to the model
        
    Returns:
        The generated response text
    """
    url = f"{OLLAMA_URL}/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    loop = asyncio.get_event_loop()
    
    def _make_request():
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            response = urllib.request.urlopen(req, timeout=120)
            result = json.loads(response.read().decode('utf-8'))
            return result.get('response', '')
        except urllib.error.URLError as e:
            return f"[Error: Cannot connect to Ollama at {OLLAMA_URL}. Make sure Ollama is running with model '{model}'. Error: {e.reason}]"
        except Exception as e:
            return f"[Error: {str(e)}]"
    
    return await loop.run_in_executor(None, _make_request)


async def stream_ollama_async(model: str, prompt: str) -> AsyncGenerator[str, None]:
    """
    Stream response from Ollama API.
    
    Args:
        model: The model name to use
        prompt: The prompt to send
        
    Yields:
        Response tokens as they are generated
    """
    url = f"{OLLAMA_URL}/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }

    loop = asyncio.get_event_loop()
    
    def _stream_request():
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            response = urllib.request.urlopen(req, timeout=120)
            
            chunks = []
            for line in response:
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            chunks.append(chunk['response'])
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            return chunks
        except urllib.error.URLError as e:
            return [f"[Error: Cannot connect to Ollama. Make sure Ollama is running. Error: {e.reason}]"]
        except Exception as e:
            return [f"[Error: {str(e)}]"]
    
    chunks = await loop.run_in_executor(None, _stream_request)
    for chunk in chunks:
        yield chunk


class MemoryScopedAgent:
    """
    Base class for memory-scoped agents with Ollama integration.
    
    Attributes:
        id: Unique identifier for the agent
        name: Human-readable name
        model: Ollama model to use for generation
        memory_config: Configuration for memory scoping
    """

    id: str = "memory-agent-base"
    name: str = "Memory Agent Base"
    model: str = "lacy:latest"
    memory_config: Dict[str, Any] = {}
    version: str = "1.0.0"

    def __init__(self):
        """Initialize the agent with empty memory and conversation history."""
        self.memory: Dict[str, Any] = {}
        self.conversation_history: list = []
        self.created_at: datetime = datetime.now()

    def _build_prompt(self, text: str, memory_context: Optional[Dict]) -> str:
        """
        Build the full prompt for Ollama including context.
        
        Args:
            text: The user's message
            memory_context: Optional memory context to include
            
        Returns:
            The complete prompt string
        """
        parts = []

        # Add system context from memory config
        if self.memory_config.get('template'):
            parts.append(self.memory_config['template'])

        # Add memory context if available
        if memory_context:
            parts.append(f"\nContext from memory:\n{memory_context}")

        # Add conversation history (last 10 messages for context)
        if self.conversation_history:
            history_text = "\n".join([
                f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}"
                for h in self.conversation_history[-10:]
            ])
            parts.append(f"\nRecent conversation:\n{history_text}")

        # Add current user message
        parts.append(f"\nUser: {text}")
        parts.append("\nAssistant:")

        return "\n".join(parts)

    def generate_response(self, text: str, memory_context: Optional[Dict] = None,
                         resource: str = "default", thread: str = "default",
                         tool_loader=None) -> str:
        """
        Generate a response using Ollama (synchronous).
        
        Args:
            text: The user's message
            memory_context: Optional memory context
            resource: Resource identifier for memory scoping
            thread: Thread identifier for memory scoping
            tool_loader: Optional tool loader for tool execution
            
        Returns:
            The generated response
        """
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.generate_response_async(text, memory_context, resource, thread, tool_loader)
            )
        finally:
            loop.close()

    async def generate_response_async(self, text: str, memory_context: Optional[Dict] = None,
                                      resource: str = "default", thread: str = "default",
                                      tool_loader=None) -> str:
        """
        Generate a response using Ollama (async).
        
        Args:
            text: The user's message
            memory_context: Optional memory context
            resource: Resource identifier for memory scoping
            thread: Thread identifier for memory scoping
            tool_loader: Optional tool loader for tool execution
            
        Returns:
            The generated response
        """
        # Store user message in history
        self.conversation_history.append({
            "role": "user", 
            "content": text,
            "timestamp": datetime.now().isoformat()
        })

        # Build prompt and call Ollama
        prompt = self._build_prompt(text, memory_context)
        response = await call_ollama_async(self.model, prompt)

        # Store assistant response in history
        self.conversation_history.append({
            "role": "assistant", 
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    async def stream_response(self, text: str, memory_context: Optional[Dict] = None,
                             resource: str = "default", thread: str = "default",
                             tool_loader=None) -> AsyncGenerator[str, None]:
        """
        Stream a response from Ollama.
        
        Args:
            text: The user's message
            memory_context: Optional memory context
            resource: Resource identifier for memory scoping
            thread: Thread identifier for memory scoping
            tool_loader: Optional tool loader for tool execution
            
        Yields:
            Response tokens as they are generated
        """
        # Store user message in history
        self.conversation_history.append({
            "role": "user", 
            "content": text,
            "timestamp": datetime.now().isoformat()
        })

        # Build prompt
        prompt = self._build_prompt(text, memory_context)

        # Stream from Ollama
        full_response = ""
        async for chunk in stream_ollama_async(self.model, prompt):
            full_response += chunk
            yield chunk

        # Store complete response in history
        self.conversation_history.append({
            "role": "assistant", 
            "content": full_response,
            "timestamp": datetime.now().isoformat()
        })

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []

    def get_metadata(self) -> Dict[str, Any]:
        """Get agent metadata."""
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "memory_scope": self.memory_config.get("scope", "global"),
            "conversation_length": len(self.conversation_history)
        }


class ResourceScopedAgent(MemoryScopedAgent):
    """
    Agent with resource-scoped memory.
    Maintains context across all interactions within a resource.
    """

    id = "personal-assistant-resource"
    name = "PersonalAssistantResource"
    model = "lacy:latest"
    memory_config = {
        "scope": "resource",
        "template": """You are a helpful AI assistant with resource-scoped memory.
You maintain context across all interactions within a resource.

# User Profile
- **Name**:
- **Location**:
- **Interests**:
- **Preferences**:
- **Long-term Goals**:
"""
    }


class ThreadScopedAgent(MemoryScopedAgent):
    """
    Agent with thread-scoped memory.
    Maintains context only within the current conversation thread.
    """

    id = "personal-assistant-thread"
    name = "PersonalAssistantThread"
    model = "lacy:latest"
    memory_config = {
        "scope": "thread",
        "template": """You are a helpful AI assistant with thread-scoped memory.
You maintain context only within the current conversation thread.

# User Profile
- **Name**:
- **Interests**:
- **Current Goal**:
"""
    }


class LacyAgent(MemoryScopedAgent):
    """
    Default Lacy agent for general assistance.
    A warm, precise, and helpful AI companion.
    """

    id = "lacy"
    name = "Lacy"
    model = "lacy:latest"
    version = "1.0.0"
    memory_config = {
        "scope": "resource",
        "template": """You are Lacy, a helpful AI assistant. You are warm, precise, and helpful.
You help users with coding, questions, and general tasks.

Be direct and helpful. Provide clear, actionable responses.
"""
    }


# Export agents
__all__ = [
    'MemoryScopedAgent', 
    'ResourceScopedAgent', 
    'ThreadScopedAgent', 
    'LacyAgent',
    'call_ollama_async',
    'stream_ollama_async'
]
