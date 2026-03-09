"""
Database connection pooling utilities for SQLite (and pluggable for other DBs).
"""
from sqlite3 import connect
from threading import Lock
from queue import Queue
from typing import Any


class SQLitePool:
    def __init__(self, db_path: str, pool_size: int = 10):
        self.db_path = db_path
        self.pool = Queue(maxsize=pool_size)
        self.lock = Lock()

        for _ in range(pool_size):
            conn = connect(db_path, check_same_thread=False)
            conn.row_factory = lambda cursor, row: dict(zip([c[0] for c in cursor.description], row))
            self.pool.put(conn)

    def get_connection(self):
        return self.pool.get()

    def return_connection(self, conn: Any):
        try:
            self.pool.put(conn)
        except Exception:
            conn.close()

    def close_all(self):
        while not self.pool.empty():
            conn = self.pool.get_nowait()
            conn.close()
