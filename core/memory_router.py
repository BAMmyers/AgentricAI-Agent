"""
AgentricAI Memory Router.
Routes memory operations to appropriate storage backends with conversation persistence.
"""
import json
import sqlite3
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# caching and pooling
from core.cache_layer import CacheLayer
from core.database import SQLitePool
from core.config import get_config


class MemoryScope(Enum):
    """Memory scope types for different persistence levels."""
    GLOBAL = "global"          # Shared across all agents
    AGENT = "agent"            # Agent-specific memory
    RESOURCE = "resource"      # Resource-scoped memory
    THREAD = "thread"          # Thread-scoped memory
    SESSION = "session"        # Session-scoped memory


class MemoryType(Enum):
    """Memory content types."""
    CONVERSATION = "conversation"
    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    EMBEDDING = "embedding"
    DOCUMENT = "document"


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    key: str
    value: Any
    scope: MemoryScope
    scope_id: str
    memory_type: MemoryType
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'scope': self.scope.value,
            'scope_id': self.scope_id,
            'type': self.memory_type.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }


class SQLiteMemoryBackend:
    """
    SQLite-based memory storage with conversation persistence.
    
    Features:
    - Conversation history persistence
    - Scoped memory (resource, thread, agent, global)
    - Memory search capabilities
    - Automatic cleanup of old entries
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the SQLite backend.
        
        Args:
            db_path: Path to the SQLite database file
        """
        cfg = get_config()
        self.db_path = db_path or cfg.memory_db_path or str(Path(__file__).parent.parent / "memory.db")
        # initialize pool and cache
        self.pool = SQLitePool(self.db_path, pool_size=10)
        self.cache = CacheLayer(cfg.redis_url)
        # if deployment_mode distributed, ensure cache initialized later
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        # create using a direct connection to avoid pool ordering issues
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Memory entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                scope TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT,
                UNIQUE(key, scope, scope_id)
            )
        ''')
        
        # Conversation history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource TEXT NOT NULL,
                thread TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory(scope, scope_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_resource ON conversations(resource, thread)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)')
        
        conn.commit()
        conn.close()
    
    
    def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry."""
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO memory 
                (id, key, value, scope, scope_id, type, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.id,
                entry.key,
                json.dumps(entry.value),
                entry.scope.value,
                entry.scope_id,
                entry.memory_type.value,
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
                json.dumps(entry.metadata)
            ))
            
            conn.commit()
            self.pool.return_connection(conn)
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    def retrieve(self, key: str, scope: MemoryScope, scope_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry."""
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, key, value, scope, scope_id, type, created_at, updated_at, metadata
                FROM memory WHERE key = ? AND scope = ? AND scope_id = ?
            ''', (key, scope.value, scope_id))
            
            row = cursor.fetchone()
            self.pool.return_connection(conn)
            
            if row:
                return MemoryEntry(
                    id=row[0],
                    key=row[1],
                    value=json.loads(row[2]),
                    scope=MemoryScope(row[3]),
                    scope_id=row[4],
                    memory_type=MemoryType(row[5]),
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                    metadata=json.loads(row[8]) if row[8] else {}
                )
            return None
        except Exception as e:
            print(f"Error retrieving memory: {e}")
            return None
    
    def search(self, query: str, scope: MemoryScope, scope_id: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memory entries using pooled connection."""
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, key, value, scope, scope_id, type, created_at, updated_at, metadata
                FROM memory 
                WHERE scope = ? AND scope_id = ? AND (key LIKE ? OR value LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (scope.value, scope_id, f'%{query}%', f'%{query}%', limit))
            
            rows = cursor.fetchall()
            self.pool.return_connection(conn)
            
            entries = []
            for row in rows:
                entries.append(MemoryEntry(
                    id=row[0],
                    key=row[1],
                    value=json.loads(row[2]),
                    scope=MemoryScope(row[3]),
                    scope_id=row[4],
                    memory_type=MemoryType(row[5]),
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                    metadata=json.loads(row[8]) if row[8] else {}
                ))
            
            return entries
        except Exception as e:
            print(f"Error searching memory: {e}")
            return []
    
    def delete(self, key: str, scope: MemoryScope, scope_id: str) -> bool:
        """Delete a memory entry using pooled connection."""
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM memory WHERE key = ? AND scope = ? AND scope_id = ?
            ''', (key, scope.value, scope_id))
            
            conn.commit()
            self.pool.return_connection(conn)
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def list_all(self, scope: MemoryScope, scope_id: str) -> List[MemoryEntry]:
        """List all memory entries for a scope using pooled connection."""
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, key, value, scope, scope_id, type, created_at, updated_at, metadata
                FROM memory WHERE scope = ? AND scope_id = ?
                ORDER BY updated_at DESC
            ''', (scope.value, scope_id))
            
            rows = cursor.fetchall()
            self.pool.return_connection(conn)
            
            entries = []
            for row in rows:
                entries.append(MemoryEntry(
                    id=row[0],
                    key=row[1],
                    value=json.loads(row[2]),
                    scope=MemoryScope(row[3]),
                    scope_id=row[4],
                    memory_type=MemoryType(row[5]),
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                    metadata=json.loads(row[8]) if row[8] else {}
                ))
            
            return entries
        except Exception as e:
            print(f"Error listing memory: {e}")
            return []
    
    # Conversation-specific methods
    
    def save_conversation_message(self, resource: str, thread: str, role: str, 
                                  content: str, metadata: Dict = None) -> int:
        """
        Save a conversation message.
        
        Args:
            resource: Resource identifier
            thread: Thread identifier
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata
            
        Returns:
            The inserted message ID
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversations (resource, thread, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                resource,
                thread,
                role,
                content,
                datetime.now().isoformat(),
                json.dumps(metadata) if metadata else None
            ))
            
            msg_id = cursor.lastrowid
            conn.commit()
            self.pool.return_connection(conn)
            return msg_id
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return -1
    
    def get_conversation_history(self, resource: str, thread: str, 
                                 limit: int = 50) -> List[Dict]:
        """
        Get conversation history for a resource/thread.
        
        Args:
            resource: Resource identifier
            thread: Thread identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, role, content, timestamp, metadata
                FROM conversations 
                WHERE resource = ? AND thread = ?
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (resource, thread, limit))
            
            rows = cursor.fetchall()
            self.pool.return_connection(conn)
            
            messages = []
            for row in rows:
                messages.append({
                    'id': row[0],
                    'role': row[1],
                    'content': row[2],
                    'timestamp': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {}
                })
            
            return messages
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def clear_conversation(self, resource: str, thread: str) -> bool:
        """Clear conversation history for a resource/thread."""
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM conversations WHERE resource = ? AND thread = ?
            ''', (resource, thread))
            
            conn.commit()
            self.pool.return_connection(conn)
            return True
        except Exception as e:
            print(f"Error clearing conversation: {e}")
            return False


class MemoryRouter:
    """
    Routes memory operations to appropriate backends.
    
    Provides high-level memory management with:
    - Scoped memory storage
    - Conversation persistence
    - Caching for performance
    """
    
    def __init__(self, backend: SQLiteMemoryBackend = None):
        """
        Initialize the memory router.
        
        Args:
            backend: Optional custom backend
        """
        self.backend = backend or SQLiteMemoryBackend()
        self._cache: Dict[str, MemoryEntry] = {}
        # initialize redis cache if available
        try:
            import asyncio
            asyncio.run(self.backend.cache.init())
        except Exception:
            pass
    
    def _cache_key(self, key: str, scope: MemoryScope, scope_id: str) -> str:
        """Generate cache key."""
        return f"{scope.value}:{scope_id}:{key}"
    
    def store(self, key: str, value: Any, scope: MemoryScope = MemoryScope.GLOBAL, 
              scope_id: str = "default", memory_type: MemoryType = MemoryType.FACT,
              metadata: Dict = None) -> MemoryEntry:
        """Store a memory entry."""
        import uuid
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            key=key,
            value=value,
            scope=scope,
            scope_id=scope_id,
            memory_type=memory_type,
            metadata=metadata or {}
        )
        
        self.backend.store(entry)
        self._cache[self._cache_key(key, scope, scope_id)] = entry
        
        return entry
    
    def retrieve(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL, 
                 scope_id: str = "default") -> Optional[Any]:
        """Retrieve a memory value."""
        cache_key = self._cache_key(key, scope, scope_id)
        
        if cache_key in self._cache:
            return self._cache[cache_key].value
        
        entry = self.backend.retrieve(key, scope, scope_id)
        if entry:
            self._cache[cache_key] = entry
            return entry.value
        
        return None
    
    def read_memory(self, resource_id: str, thread_id: str) -> Optional[Dict]:
        """
        Read memory for a resource/thread (legacy interface).
        
        Args:
            resource_id: Resource identifier
            thread_id: Thread identifier
            
        Returns:
            Memory context dictionary
        """
        # Get conversation history
        history = self.backend.get_conversation_history(resource_id, thread_id)
        
        # Get resource-scoped memory
        resource_memory = self.backend.list_all(MemoryScope.RESOURCE, resource_id)
        
        # Get thread-scoped memory
        thread_memory = self.backend.list_all(MemoryScope.THREAD, thread_id)
        
        return {
            'conversation_history': history,
            'resource_memory': [e.to_dict() for e in resource_memory],
            'thread_memory': [e.to_dict() for e in thread_memory]
        }
    
    def write_memory(self, resource_id: str, thread_id: str, message: str) -> bool:
        """
        Write memory for a resource/thread (legacy interface).
        
        Args:
            resource_id: Resource identifier
            thread_id: Thread identifier
            message: Message to store
            
        Returns:
            Success status
        """
        return self.backend.save_conversation_message(
            resource=resource_id,
            thread=thread_id,
            role='user',
            content=message
        ) > 0
    
    def search(self, query: str, scope: MemoryScope = MemoryScope.GLOBAL,
               scope_id: str = "default", limit: int = 10) -> List[Dict]:
        """Search memory entries."""
        entries = self.backend.search(query, scope, scope_id, limit)
        return [e.to_dict() for e in entries]
    
    def delete(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL,
               scope_id: str = "default") -> bool:
        """Delete a memory entry."""
        cache_key = self._cache_key(key, scope, scope_id)
        
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        return self.backend.delete(key, scope, scope_id)
    
    def list_all(self, scope: MemoryScope = MemoryScope.GLOBAL,
                 scope_id: str = "default") -> List[Dict]:
        """List all memory entries."""
        entries = self.backend.list_all(scope, scope_id)
        return [e.to_dict() for e in entries]
    
    # Convenience methods
    
    def save_conversation(self, resource: str, thread: str, role: str, 
                         content: str, metadata: Dict = None) -> int:
        """Save a conversation message."""
        return self.backend.save_conversation_message(resource, thread, role, content, metadata)
    
    def get_conversation(self, resource: str, thread: str, limit: int = 50) -> List[Dict]:
        """Get conversation history, using cache if available."""
        # attempt cache lookup if backend provides async cache
        try:
            if hasattr(self.backend, 'cache') and self.backend.cache.redis:
                # run asynchronously to avoid blocking event loop
                cached = asyncio.run(self.backend.cache.get_conversation(resource, thread))
                if cached is not None:
                    return cached
        except Exception:
            pass

        history = self.backend.get_conversation_history(resource, thread, limit)
        # populate cache
        try:
            if hasattr(self.backend, 'cache') and self.backend.cache.redis:
                asyncio.run(self.backend.cache.set_conversation(resource, thread, history))
        except Exception:
            pass
        return history
    
    def clear_conversation(self, resource: str, thread: str) -> bool:
        """Clear conversation history."""
        return self.backend.clear_conversation(resource, thread)


# Global memory router instance
_memory_router: Optional[MemoryRouter] = None


def get_memory_router() -> MemoryRouter:
    """Get the global memory router instance."""
    global _memory_router
    if _memory_router is None:
        _memory_router = MemoryRouter()
    return _memory_router
