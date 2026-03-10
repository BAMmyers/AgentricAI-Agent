"""
Conversation Memory Manager for AgentricAI.
Provides SQLite-based persistence for conversation history and agent memory.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass,from contextlib import contextmanager


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    id: int
    resource_id: str
    thread_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class MemoryEntry:
    """Represents a memory entry for an agent."""
    id: int
    agent_id: str
    resource_id: str
    thread_id: str
    key: str
    value: str
    scope: str  # 'global', 'resource', 'thread'
    created_at: datetime
    updated_at: datetime


class ConversationMemoryManager:
    """
    Manages conversation history and agent memory with SQLite persistence.
    
    Features:
    - Conversation history storage
    - Memory scoping (global, resource, thread)
    - Efficient querying with indexes
    - Automatic cleanup of old conversations
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the memory manager.
        
        Args:
            db_path: Path to SQLite database file. Defaults to memory.db in core directory.
        """
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "memory.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Conversation history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Memory entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    resource_id TEXT,
                    thread_id TEXT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'global',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(agent_id, resource_id, thread_id, key)
                )
            ''')
            
            # Create indexes for efficient querying
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversation_resource_thread 
                ON conversation_history(resource_id, thread_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_memory_agent_scope 
                ON memory_entries(agent_id, scope)
            ''')
            
            conn.commit()
    
    def save_message(self, resource_id: str, thread_id: str, role: str, 
                     content: str, metadata: Dict = None) -> int:
        """
        Save a message to conversation history.
        
        Args:
            resource_id: Resource identifier
            thread_id: Thread identifier
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata dict
            
        Returns:
            The ID of the inserted message
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_history 
                (resource_id, thread_id, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (resource_id, thread_id, role, content, 
                  json.dumps(metadata) if metadata else None))
            conn.commit()
            return cursor.lastrowid
    
    def get_conversation(self, resource_id: str, thread_id: str, 
                        limit: int = 100) -> List[ConversationMessage]:
        """
        Get conversation history for a resource/thread.
        
        Args:
            resource_id: Resource identifier
            thread_id: Thread identifier
            limit: Maximum number of messages to return
            
        Returns:
            List of ConversationMessage objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, resource_id, thread_id, role, content, timestamp, metadata
                FROM conversation_history
                WHERE resource_id = ? AND thread_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (resource_id, thread_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                messages.append(ConversationMessage(
                    id=row[0],
                    resource_id=row[1],
                    thread_id=row[2],
                    role=row[3],
                    content=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    metadata=json.loads(row[6]) if row[6] else {}
                ))
            return messages
    
    def get_conversation_context(self, resource_id: str, thread_id: str, 
                                  max_messages: int = 10) -> str:
        """
        Get formatted conversation context for prompts.
        
        Args:
            resource_id: Resource identifier
            thread_id: Thread identifier
            max_messages: Maximum messages to include
            
        Returns:
            Formatted string of conversation history
        """
        messages = self.get_conversation(resource_id, thread_id, max_messages)
        if not messages:
            return ""
        
        lines = []
        for msg in messages[-max_messages:]:
            lines.append(f"{msg.role.capitalize()}: {msg.content}")
        
        return "\n".join(lines)
    
    def store_memory(self, agent_id: str, key: str, value: str, 
                     scope: str = 'global', resource_id: str = None, 
                     thread_id: str = None) -> int:
        """
        Store a memory entry.
        
        Args:
            agent_id: Agent identifier
            key: Memory key
            value: Memory value
            scope: Memory scope ('global', 'resource', 'thread')
            resource_id: Resource identifier (for resource scope)
            thread_id: Thread identifier (for thread scope)
            
        Returns:
            The ID of the inserted/updated entry
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO memory_entries 
                (agent_id, resource_id, thread_id, key, value, scope, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(agent_id, resource_id, thread_id, key)
                DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            ''', (agent_id, resource_id, thread_id, key, value, scope))
            conn.commit()
            return cursor.lastrowid
    
    def retrieve_memory(self, agent_id: str, key: str, 
                       scope: str = 'global', resource_id: str = None,
                       thread_id: str = None) -> Optional[str]:
        """
        Retrieve a memory entry.
        
        Args:
            agent_id: Agent identifier
            key: Memory key
            scope: Memory scope
            resource_id: Resource identifier
            thread_id: Thread identifier
            
        Returns:
            Memory value or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT value FROM memory_entries
                WHERE agent_id = ? AND key = ? AND scope = ?
                AND (resource_id = ? OR resource_id IS NULL)
                AND (thread_id = ? OR thread_id IS NULL)
            ''', (agent_id, key, scope, resource_id, thread_id))
            
            row = cursor.fetchone()
            return row[0] if row else None
    
    def clear_conversation(self, resource_id: str, thread_id: str):
        """
        Clear conversation history for a resource/thread.
        
        Args:
            resource_id: Resource identifier
            thread_id: Thread identifier
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM conversation_history
                WHERE resource_id = ? AND thread_id = ?
            ''', (resource_id, thread_id))
            conn.commit()
    
    def cleanup_old_conversations(self, days_old: int = 30):
        """
        Remove conversations older than specified days.
        
        Args:
            days_old: Number of days after which to remove conversations
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM conversation_history
                WHERE timestamp < datetime('now', ? || ' days')
            ''', (f'-{days_old} days',))
            conn.commit()


# Global instance
_memory_manager: Optional[ConversationMemoryManager] = None


def get_memory_manager(db_path: str = None) -> ConversationMemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ConversationMemoryManager(db_path)
    return _memory_manager
