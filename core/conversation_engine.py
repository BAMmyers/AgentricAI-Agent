"""
AgentricAI Conversation Engine.
Handles conversation flow between users and agents with memory integration.
"""
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from core.tracing import get_tracer


class ConversationEngine:
    """
    Manages conversations between users and agents.
    
    Coordinates:
    - Agent loading and selection
    - Memory context retrieval
    - Response generation (sync and streaming)
    - Memory persistence after conversations
    """
    
    def __init__(self, agent_loader, tool_loader, memory_router):
        """
        Initialize the conversation engine.
        
        Args:
            agent_loader: The agent loader instance
            tool_loader: The tool loader instance
            memory_router: The memory router instance
        """
        self.agent_loader = agent_loader
        self.tool_loader = tool_loader
        self.memory_router = memory_router

    async def generate_response(
        self, 
        agent_id: str, 
        text: str, 
        resource: str, 
        thread: str, 
        memory_context: Optional[Dict]
    ) -> str:
        """
        Generate a complete response from an agent.
        
        Args:
            agent_id: The ID of the agent to use
            text: The user's message
            resource: Resource identifier for memory scoping
            thread: Thread identifier for memory scoping
            memory_context: Pre-loaded memory context
            
        Returns:
            The complete response text
        """
        agent = self.agent_loader.get_agent(agent_id)
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("engine_generate_response") as span:
            span.set_attribute("agent_id", agent_id)
            span.set_attribute("resource", resource)
            span.set_attribute("thread", thread)
            # Check if agent has async method
            if hasattr(agent, 'generate_response_async'):
                response = await agent.generate_response_async(
                    text=text,
                    memory_context=memory_context,
                    resource=resource,
                    thread=thread,
                    tool_loader=self.tool_loader
                )
            else:
                # Fallback to sync method
                response = agent.generate_response(
                    text=text,
                    memory_context=memory_context,
                    resource=resource,
                    thread=thread,
                    tool_loader=self.tool_loader
                )
        return response

    async def stream_response(
        self, 
        agent_id: str, 
        text: str, 
        resource: str, 
        thread: str, 
        memory_context: Optional[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from an agent.
        
        Args:
            agent_id: The ID of the agent to use
            text: The user's message
            resource: Resource identifier for memory scoping
            thread: Thread identifier for memory scoping
            memory_context: Pre-loaded memory context
            
        Yields:
            Response tokens as they are generated
        """
        agent = self.agent_loader.get_agent(agent_id)
        
        # Get the stream generator
        stream = agent.stream_response(
            text=text,
            memory_context=memory_context,
            resource=resource,
            thread=thread,
            tool_loader=self.tool_loader
        )
        
        # Handle both async and sync generators
        if hasattr(stream, '__aiter__'):
            # Async generator
            async for chunk in stream:
                yield chunk
        else:
            # Sync generator - wrap for async iteration
            for chunk in stream:
                yield chunk
                await asyncio.sleep(0)  # Yield control to event loop
        
        # Store in memory after streaming completes
        try:
            self.memory_router.write_memory(
                resource_id=resource,
                thread_id=thread,
                message=text
            )
        except Exception as e:
            # Log but don't fail the response
            print(f"[ConversationEngine] Memory write failed: {e}")

    def get_conversation_context(
        self, 
        resource: str, 
        thread: str
    ) -> Optional[Dict]:
        """
        Retrieve conversation context from memory.
        
        Args:
            resource: Resource identifier
            thread: Thread identifier
            
        Returns:
            Memory context dict or None
        """
        try:
            return self.memory_router.read_memory(resource, thread)
        except Exception:
            return None
