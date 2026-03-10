"""
AgentricAI Event Loop.
Provides async event processing and task scheduling.
"""
import asyncio
from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class EventType(Enum):
    """Event types for the event loop."""
    CHAT_MESSAGE = "chat_message"
    AGENT_RESPONSE = "agent_response"
    TOOL_EXECUTION = "tool_execution"
    MEMORY_UPDATE = "memory_update"
    SYSTEM = "system"
    ERROR = "error"


@dataclass
class Event:
    """An event in the system."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.SYSTEM
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    target: Optional[str] = None
    priority: int = 0
    processed: bool = False


class EventHandler:
    """Base class for event handlers."""
    
    async def handle(self, event: Event) -> Optional[Event]:
        """Handle an event and optionally return a new event."""
        raise NotImplementedError


class EventLoop:
    """
    Async event loop for processing events.
    
    Features:
    - Event queue with priority
    - Handler registration
    - Event filtering
    - Async processing
    """
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the event loop.
        
        Args:
            max_queue_size: Maximum events in queue
        """
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._event_count: int = 0
    
    def register_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Register a handler for an event type.
        
        Args:
            event_type: The event type to handle
            handler: The handler instance
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: EventType, handler: EventHandler) -> bool:
        """Unregister a handler."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False
    
    async def emit(self, event: Event) -> None:
        """
        Emit an event to the queue.
        
        Args:
            event: The event to emit
        """
        # Priority queue uses (priority, counter, event) for ordering
        await self._queue.put((event.priority, self._event_count, event))
        self._event_count += 1
    
    async def emit_data(
        self, 
        event_type: EventType, 
        data: Dict[str, Any],
        source: str = "system",
        target: Optional[str] = None,
        priority: int = 0
    ) -> Event:
        """
        Emit an event with data.
        
        Args:
            event_type: Type of event
            data: Event data
            source: Event source
            target: Optional target
            priority: Event priority (lower = higher priority)
            
        Returns:
            The created event
        """
        event = Event(
            type=event_type,
            data=data,
            source=source,
            target=target,
            priority=priority
        )
        await self.emit(event)
        return event
    
    async def _process_event(self, event: Event) -> None:
        """Process a single event."""
        handlers = self._handlers.get(event.type, [])
        
        for handler in handlers:
            try:
                result = await handler.handle(event)
                if result:
                    await self.emit(result)
            except Exception as e:
                # Emit error event
                await self.emit_data(
                    EventType.ERROR,
                    {"error": str(e), "original_event": event.id},
                    source="event_loop"
                )
        
        event.processed = True
    
    async def _run_loop(self) -> None:
        """Main event processing loop."""
        while self._running:
            try:
                # Wait for event with timeout
                priority, count, event = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                
                # Process the event
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                # No events, continue loop
                continue
            except Exception as e:
                print(f"[EventLoop] Error processing event: {e}")
    
    def start(self) -> None:
        """Start the event loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
    
    async def stop(self) -> None:
        """Stop the event loop gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    @property
    def is_running(self) -> bool:
        """Check if the loop is running."""
        return self._running
    
    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


class ChatEventHandler(EventHandler):
    """Handler for chat events."""
    
    def __init__(self, conversation_engine, memory_router):
        self.conversation_engine = conversation_engine
        self.memory_router = memory_router
    
    async def handle(self, event: Event) -> Optional[Event]:
        """Handle a chat message event."""
        if event.type != EventType.CHAT_MESSAGE:
            return None
        
        text = event.data.get("text")
        agent_id = event.data.get("agent_id", "lacy")
        resource = event.data.get("resource", "default")
        thread = event.data.get("thread", "default")
        
        if not text:
            return None
        
        # Get memory context
        memory_context = self.memory_router.read_memory(resource, thread)
        
        # Generate response
        response = await self.conversation_engine.generate_response(
            agent_id=agent_id,
            text=text,
            resource=resource,
            thread=thread,
            memory_context=memory_context
        )
        
        # Return agent response event
        return Event(
            type=EventType.AGENT_RESPONSE,
            data={
                "response": response,
                "agent_id": agent_id,
                "resource": resource,
                "thread": thread
            },
            source="chat_handler",
            target=event.source
        )


class LoggingEventHandler(EventHandler):
    """Handler that logs all events."""
    
    def __init__(self, log_file: str = "events.log"):
        self.log_file = log_file
    
    async def handle(self, event: Event) -> Optional[Event]:
        """Log the event."""
        from datetime import datetime
        log_entry = f"{datetime.now().isoformat()} | {event.type.value} | {event.source} | {event.data}\n"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass
        
        return None  # Don't emit new event


# Global event loop instance
_event_loop: Optional[EventLoop] = None


def get_event_loop() -> EventLoop:
    """Get the global event loop instance."""
    global _event_loop
    if _event_loop is None:
        _event_loop = EventLoop()
    return _event_loop
