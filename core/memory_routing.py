"""
AgentricAI - Memory Routing System
Routes memory operations to appropriate storage backends.
"""
import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class MemoryScope(Enum):
    """Memory scope types."""
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
    embedding: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
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


class MemoryBackend:
    """Base class for memory backends."""
    
    def store(self, entry: MemoryEntry) -> bool:
        raise NotImplementedError
    
    def retrieve(self, key: str, scope: MemoryScope, scope_id: str) -> Optional[MemoryEntry]:
        raise NotImplementedError
    
    def search(self, query: str, scope: MemoryScope, scope_id: str, limit: int = 10) -> List[MemoryEntry]:
        raise NotImplementedError
    
    def delete(self, key: str, scope: MemoryScope, scope_id: str) -> bool:
        raise NotImplementedError
    
    def list_all(self, scope: MemoryScope, scope_id: str) -> List[MemoryEntry]:
        raise NotImplementedError


class SQLiteMemoryBackend(MemoryBackend):
    """SQLite-based memory storage."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path(__file__).parent.parent / 'memory.db')
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                embedding BLOB,
                UNIQUE(key, scope, scope_id)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory(scope, scope_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key)
        ''')
        
        conn.commit()
        conn.close()
    
    def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO memory 
                (id, key, value, scope, scope_id, type, created_at, updated_at, metadata, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.id,
                entry.key,
                json.dumps(entry.value),
                entry.scope.value,
                entry.scope_id,
                entry.memory_type.value,
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
                json.dumps(entry.metadata),
                json.dumps(entry.embedding) if entry.embedding else None
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False
    
    def retrieve(self, key: str, scope: MemoryScope, scope_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, key, value, scope, scope_id, type, created_at, updated_at, metadata, embedding
                FROM memory WHERE key = ? AND scope = ? AND scope_id = ?
            ''', (key, scope.value, scope_id))
            
            row = cursor.fetchone()
            conn.close()
            
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
                    metadata=json.loads(row[8]) if row[8] else {},
                    embedding=json.loads(row[9]) if row[9] else []
                )
            return None
        except Exception as e:
            print(f"Error retrieving memory: {e}")
            return None
    
    def search(self, query: str, scope: MemoryScope, scope_id: str, limit: int = 10) -> List[MemoryEntry]:
        """Search memory entries by key or value."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, key, value, scope, scope_id, type, created_at, updated_at, metadata, embedding
                FROM memory 
                WHERE scope = ? AND scope_id = ? AND (key LIKE ? OR value LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (scope.value, scope_id, f'%{query}%', f'%{query}%', limit))
            
            rows = cursor.fetchall()
            conn.close()
            
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
                    metadata=json.loads(row[8]) if row[8] else {},
                    embedding=json.loads(row[9]) if row[9] else []
                ))
            
            return entries
        except Exception as e:
            print(f"Error searching memory: {e}")
            return []
    
    def delete(self, key: str, scope: MemoryScope, scope_id: str) -> bool:
        """Delete a memory entry."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM memory WHERE key = ? AND scope = ? AND scope_id = ?
            ''', (key, scope, scope_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}")
            return False
    
    def list_all(self, scope: MemoryScope, scope_id: str) -> List[MemoryEntry]:
        """List all memory entries for a scope."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, key, value, scope, scope_id, type, created_at, updated_at, metadata, embedding
                FROM memory WHERE scope = ? AND scope_id = ?
                ORDER BY updated_at DESC
            ''', (scope.value, scope_id))
            
            rows = cursor.fetchall()
            conn.close()
            
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
                    metadata=json.loads(row[8]) if row[8] else {},
                    embedding=json.loads(row[9]) if row[9] else []
                ))
            
            return entries
        except Exception as e:
            print(f"Error listing memory: {e}")
            return []


class MemoryRouter:
    """Routes memory operations to appropriate backends."""
    
    def __init__(self, backend: MemoryBackend = None):
        self.backend = backend or SQLiteMemoryBackend()
        self._cache: Dict[str, MemoryEntry] = {}
    
    def _cache_key(self, key: str, scope: MemoryScope, scope_id: str) -> str:
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
        
        # Store in backend
        self.backend.store(entry)
        
        # Update cache
        self._cache[self._cache_key(key, scope, scope_id)] = entry
        
        return entry
    
    def retrieve(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL, 
                 scope_id: str = "default") -> Optional[Any]:
        """Retrieve a memory value."""
        cache_key = self._cache_key(key, scope, scope_id)
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key].value
        
        # Retrieve from backend
        entry = self.backend.retrieve(key, scope, scope_id)
        if entry:
            self._cache[cache_key] = entry
            return entry.value
        
        return None
    
    def search(self, query: str, scope: MemoryScope = MemoryScope.GLOBAL,
               scope_id: str = "default", limit: int = 10) -> List[Dict]:
        """Search memory entries."""
        entries = self.backend.search(query, scope, scope_id, limit)
        return [e.to_dict() for e in entries]
    
    def delete(self, key: str, scope: MemoryScope = MemoryScope.GLOBAL,
               scope_id: str = "default") -> bool:
        """Delete a memory entry."""
        cache_key = self._cache_key(key, scope, scope_id)
        
        # Remove from cache
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        # Remove from backend
        return self.backend.delete(key, scope, scope_id)
    
    def list_all(self, scope: MemoryScope = MemoryScope.GLOBAL,
                 scope_id: str = "default") -> List[Dict]:
        """List all memory entries."""
        entries = self.backend.list_all(scope, scope_id)
        return [e.to_dict() for e in entries]
    
    # Convenience methods for common scopes
    def store_agent_memory(self, agent_id: str, key: str, value: Any, **kwargs):
        """Store agent-specific memory."""
        return self.store(key, value, MemoryScope.AGENT, agent_id, **kwargs)
    
    def retrieve_agent_memory(self, agent_id: str, key: str) -> Optional[Any]:
        """Retrieve agent-specific memory."""
        return self.retrieve(key, MemoryScope.AGENT, agent_id)
    
    def store_thread_memory(self, thread_id: str, key: str, value: Any, **kwargs):
        """Store thread-specific memory."""
        return self.store(key, value, MemoryScope.THREAD, thread_id, **kwargs)
    
    def retrieve_thread_memory(self, thread_id: str, key: str) -> Optional[Any]:
        """Retrieve thread-specific memory."""
        return self.retrieve(key, MemoryScope.THREAD, thread_id)
    
    def store_resource_memory(self, resource_id: str, key: str, value: Any, **kwargs):
        """Store resource-specific memory."""
        return self.store(key, value, MemoryScope.RESOURCE, resource_id, **kwargs)
    
    def retrieve_resource_memory(self, resource_id: str, key: str) -> Optional[Any]:
        """Retrieve resource-specific memory."""
        return self.retrieve(key, MemoryScope.RESOURCE, resource_id)


# Global memory router instance
_memory_router = None

def get_memory_router() -> MemoryRouter:
    """Get the global memory router instance."""
    global _memory_router
    if _memory_router is None:
        _memory_router = MemoryRouter()
    return _memory_router
