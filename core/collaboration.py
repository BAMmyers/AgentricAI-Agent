"""
WebSocket-based Real-Time Collaboration Module

Enables multiple users to collaborate on shared conversations with real-time
message synchronization, presence awareness, and session management.
"""

from typing import Dict, Set, Optional, List, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import asyncio
import json
import uuid
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types."""
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    CHAT_MESSAGE = "chat_message"
    TYPING = "typing"
    STOP_TYPING = "stop_typing"
    AGENT_RESPONSE = "agent_response"
    SESSION_STATE = "session_state"
    ERROR = "error"


@dataclass
class CollaborationMessage:
    """Represents a collaboration message."""
    type: str
    user_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resource: str = "default"
    thread: str = "default"
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class UserPresence:
    """Track active user in a session."""
    user_id: str
    name: str
    status: str = "active"  # active, typing, idle
    joined_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class CollaborationSession:
    """Manages a single collaboration session."""

    def __init__(self, resource: str, thread: str):
        self.resource = resource
        self.thread = thread
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        
        # Active connections: user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User presence: user_id -> UserPresence
        self.users: Dict[str, UserPresence] = {}
        
        # Message history for this session
        self.message_history: List[CollaborationMessage] = []
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket, user_name: str):
        """Register a user connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[user_id] = websocket
            self.users[user_id] = UserPresence(user_id=user_id, name=user_name)
            
        logger.info(f"User {user_id} connected to session {self.session_id}")

    async def disconnect(self, user_id: str):
        """Remove a user connection."""
        async with self._lock:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            if user_id in self.users:
                del self.users[user_id]
                
        logger.info(f"User {user_id} disconnected from session {self.session_id}")

    async def broadcast(
        self,
        message: CollaborationMessage,
        exclude_user: Optional[str] = None
    ):
        """Send message to all connected users."""
        message_dict = message.to_dict()
        dead_connections = []

        for user_id, connection in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue

            try:
                await connection.send_json(message_dict)
            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {e}")
                dead_connections.append(user_id)

        # Remove dead connections
        for user_id in dead_connections:
            await self.disconnect(user_id)

    async def broadcast_user_list(self):
        """Send current user list to all connected users."""
        async with self._lock:
            user_list = [user.to_dict() for user in self.users.values()]

        message = CollaborationMessage(
            type=MessageType.SESSION_STATE.value,
            user_id="system",
            resource=self.resource,
            thread=self.thread,
            data={"active_users": user_list, "session_id": self.session_id}
        )

        await self.broadcast(message)

    async def add_message_to_history(self, message: CollaborationMessage):
        """Store message in history."""
        async with self._lock:
            self.message_history.append(message)

    async def get_message_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent message history."""
        async with self._lock:
            recent = self.message_history[-limit:]
            return [msg.to_dict() for msg in recent]

    async def update_user_status(self, user_id: str, status: str):
        """Update user status (typing, idle, etc)."""
        async with self._lock:
            if user_id in self.users:
                self.users[user_id].status = status
                self.users[user_id].last_activity = datetime.utcnow().isoformat()

    async def is_active(self) -> bool:
        """Check if session has active connections."""
        async with self._lock:
            return len(self.active_connections) > 0

    async def get_user_count(self) -> int:
        """Get number of active users."""
        async with self._lock:
            return len(self.active_connections)


class CollaborationManager:
    """Manages all collaboration sessions."""

    def __init__(self):
        # resource_id/thread_id -> CollaborationSession
        self.sessions: Dict[str, CollaborationSession] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_session(
        self, resource: str, thread: str
    ) -> CollaborationSession:
        """Get existing session or create new one."""
        session_key = f"{resource}/{thread}"

        async with self._lock:
            if session_key not in self.sessions:
                self.sessions[session_key] = CollaborationSession(resource, thread)
                logger.info(f"Created new collaboration session: {session_key}")

            return self.sessions[session_key]

    async def connect_user(
        self,
        resource: str,
        thread: str,
        user_id: str,
        websocket: WebSocket,
        user_name: str = None
    ):
        """Connect a user to a collaboration session."""
        if user_name is None:
            user_name = user_id

        session = await self.get_or_create_session(resource, thread)
        await session.connect(user_id, websocket, user_name)

        # Notify others that user joined
        join_message = CollaborationMessage(
            type=MessageType.USER_JOINED.value,
            user_id=user_id,
            resource=resource,
            thread=thread,
            data={"user_name": user_name}
        )
        await session.broadcast(join_message, exclude_user=user_id)

        # Send current user list to the joining user
        await session.broadcast_user_list()

        # Send message history to joining user
        history = await session.get_message_history()
        history_message = CollaborationMessage(
            type="message_history",
            user_id="system",
            resource=resource,
            thread=thread,
            data={"messages": history}
        )
        try:
            await websocket.send_json(history_message.to_dict())
        except Exception as e:
            logger.error(f"Failed to send history: {e}")

        return session

    async def disconnect_user(self, resource: str, thread: str, user_id: str):
        """Disconnect a user from a session."""
        session_key = f"{resource}/{thread}"

        if session_key in self.sessions:
            session = self.sessions[session_key]
            await session.disconnect(user_id)

            # Notify others
            leave_message = CollaborationMessage(
                type=MessageType.USER_LEFT.value,
                user_id=user_id,
                resource=resource,
                thread=thread
            )
            await session.broadcast(leave_message)

            # Send updated user list
            await session.broadcast_user_list()

            # Clean up empty sessions
            if not await session.is_active():
                async with self._lock:
                    del self.sessions[session_key]
                logger.info(f"Removed empty collaboration session: {session_key}")

    async def handle_message(
        self,
        resource: str,
        thread: str,
        user_id: str,
        message_type: str,
        data: Dict[str, Any]
    ):
        """Handle incoming message from user."""
        session_key = f"{resource}/{thread}"

        if session_key not in self.sessions:
            logger.warning(f"Message received for non-existent session: {session_key}")
            return

        session = self.sessions[session_key]

        if message_type == MessageType.CHAT_MESSAGE.value:
            # Store and broadcast chat message
            msg = CollaborationMessage(
                type=message_type,
                user_id=user_id,
                resource=resource,
                thread=thread,
                data=data
            )
            await session.add_message_to_history(msg)
            await session.broadcast(msg)

        elif message_type == MessageType.TYPING.value:
            # Update user status
            await session.update_user_status(user_id, "typing")

            # Notify others
            typing_msg = CollaborationMessage(
                type=message_type,
                user_id=user_id,
                resource=resource,
                thread=thread
            )
            await session.broadcast(typing_msg, exclude_user=user_id)

        elif message_type == MessageType.STOP_TYPING.value:
            # Update user status
            await session.update_user_status(user_id, "active")

            # Notify others
            stop_msg = CollaborationMessage(
                type=message_type,
                user_id=user_id,
                resource=resource,
                thread=thread
            )
            await session.broadcast(stop_msg, exclude_user=user_id)

    async def broadcast_agent_response(
        self,
        resource: str,
        thread: str,
        agent_id: str,
        response: str,
        agent_name: str = "Agent"
    ):
        """Send agent response to all users in session."""
        session_key = f"{resource}/{thread}"

        if session_key not in self.sessions:
            return

        session = self.sessions[session_key]

        msg = CollaborationMessage(
            type=MessageType.AGENT_RESPONSE.value,
            user_id=agent_id,
            resource=resource,
            thread=thread,
            data={"response": response, "agent_name": agent_name}
        )
        await session.add_message_to_history(msg)
        await session.broadcast(msg)

    async def get_session_info(self, resource: str, thread: str) -> Dict[str, Any]:
        """Get information about a collaboration session."""
        session_key = f"{resource}/{thread}"

        if session_key not in self.sessions:
            return {"exists": False}

        session = self.sessions[session_key]

        return {
            "exists": True,
            "session_id": session.session_id,
            "resource": resource,
            "thread": thread,
            "active_users": len(await asyncio.get_running_loop().run_in_executor(
                None, lambda: session.active_connections
            )),
            "message_count": len(await asyncio.get_running_loop().run_in_executor(
                None, lambda: session.message_history
            )),
            "created_at": session.created_at.isoformat()
        }

    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get info about all active sessions."""
        sessions_info = []

        async with self._lock:
            for session_key, session in self.sessions.items():
                resource, thread = session_key.split("/")
                sessions_info.append(await self.get_session_info(resource, thread))

        return sessions_info


# Global collaboration manager instance
collaboration_manager = CollaborationManager()
