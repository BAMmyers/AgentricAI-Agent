"""
Audit logging for compliance and security tracking.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import sqlite3
from pathlib import Path

from core.config import get_config


class AuditEventType(Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    AGENT_INVOKED = "agent_invoked"
    TOOL_EXECUTED = "tool_executed"
    MEMORY_MODIFIED = "memory_modified"
    MEMORY_DELETED = "memory_deleted"
    CONFIG_CHANGED = "config_changed"
    AUTH_FAILED = "auth_failed"
    RATE_LIMIT_HIT = "rate_limit_hit"
    SECURITY_EVENT = "security_event"
    ERROR_OCCURRED = "error_occurred"


class AuditLogger:
    """Comprehensive audit logging system."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize audit logger."""
        cfg = get_config()
        self.db_path = db_path or Path(__file__).parent.parent / "audit.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize audit database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                resource TEXT,
                action TEXT,
                details TEXT,
                status TEXT,
                ip_address TEXT,
                user_agent TEXT,
                error_message TEXT
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type)')
        
        conn.commit()
        conn.close()
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> int:
        """Log an audit event."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_log 
            (timestamp, event_type, user_id, resource, action, details, status, ip_address, user_agent, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.utcnow().isoformat(),
            event_type.value,
            user_id,
            resource,
            action,
            json.dumps(details or {}),
            status,
            ip_address,
            user_agent,
            error_message
        ))
        
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        
        return event_id
    
    async def get_user_events(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get all events for a user."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM audit_log
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    async def get_events_by_type(self, event_type: AuditEventType, limit: int = 100) -> List[Dict]:
        """Get events by type."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM audit_log
            WHERE event_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (event_type.value, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    async def get_recent_events(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get recent events."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        
        cursor.execute('''
            SELECT * FROM audit_log
            WHERE datetime(timestamp) > datetime(?, 'unixepoch')
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (cutoff, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    async def search_audit_log(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Search audit log with filters."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    async def get_audit_summary(self) -> Dict[str, Any]:
        """Get audit log summary."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Total events
        cursor.execute("SELECT COUNT(*) FROM audit_log")
        total = cursor.fetchone()[0]
        
        # Events by type
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM audit_log
            GROUP BY event_type
            ORDER BY count DESC
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Events by user
        cursor.execute("""
            SELECT user_id, COUNT(*) as count
            FROM audit_log
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
        """)
        by_user = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Failed events
        cursor.execute("SELECT COUNT(*) FROM audit_log WHERE status = 'failed'")
        failed_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_events": total,
            "by_type": by_type,
            "by_user": by_user,
            "failed_events": failed_count
        }


# Global audit logger instance
audit_logger = AuditLogger()
