import sqlite3
from pathlib import Path
from datetime import datetime


class MemoryStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL
                )
            """)

    def log(self, role: str, content: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO interactions(ts, role, content) VALUES (?, ?, ?)",
                (datetime.utcnow().isoformat(), role, content),
            )

    def set_note(self, note: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO kv_store(k, v) VALUES('note', ?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (note,),
            )

    def get_note(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT v FROM kv_store WHERE k='note'")
            row = cur.fetchone()
            return row[0] if row else None

    def last_interactions(self, limit: int = 10):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT ts, role, content FROM interactions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return cur.fetchall()