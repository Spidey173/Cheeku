import sqlite3
import os
import json
import time
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.models.schemas import ChatMessage, MessageRole
from backend.utils.logger import logger


class MemoryManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(settings.DATA_DIR, "cheeku_memory.db")
        self._init_db()
        self.short_term_history: List[ChatMessage] = []

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS kv_memory (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        updated_at REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        category TEXT DEFAULT 'note',
                        created_at REAL NOT NULL
                    )
                """)
                conn.commit()
                logger.info(f"Memory database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize memory database: {e}")

    # --- Short-term Memory (Sliding Window) ---
    def add_short_term(
        self,
        role: MessageRole,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        name: Optional[str] = None
    ):
        self.short_term_history.append(
            ChatMessage(
                role=role,
                content=content or "",
                tool_call_id=tool_call_id,
                tool_calls=tool_calls,
                name=name,
                timestamp=time.time()
            )
        )
        if len(self.short_term_history) > settings.MAX_HISTORY_TURNS * 2:
            self.short_term_history = self.short_term_history[-settings.MAX_HISTORY_TURNS * 2:]

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO conversation_history (role, content, timestamp) VALUES (?, ?, ?)",
                    (role.value, content or "", time.time())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving to long-term conversation log: {e}")

    def get_short_term(self) -> List[ChatMessage]:
        return list(self.short_term_history)

    def clear_short_term(self):
        self.short_term_history.clear()

    # --- Long-term Key-Value Memory ---
    def set_pref(self, key: str, value: Any, category: str = "general"):
        try:
            val_str = json.dumps(value) if not isinstance(value, str) else value
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO kv_memory (key, value, category, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """, (key, val_str, category, time.time()))
                conn.commit()
            logger.info(f"Memory updated: category='{category}', key='{key}'")
        except Exception as e:
            logger.error(f"Error writing to kv_memory: {e}")

    def get_pref(self, key: str, default: Any = None) -> Any:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM kv_memory WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    try:
                        return json.loads(row[0])
                    except Exception:
                        return row[0]
        except Exception as e:
            logger.error(f"Error reading kv_memory: {e}")
        return default

    def get_all_prefs(self) -> Dict[str, Any]:
        prefs = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM kv_memory")
                for k, v in cursor.fetchall():
                    try:
                        prefs[k] = json.loads(v)
                    except Exception:
                        prefs[k] = v
        except Exception as e:
            logger.error(f"Error fetching all prefs: {e}")
        return prefs

    def get_context_summary(self) -> str:
        """Summarizes user profile and saved facts to inject into system prompt."""
        prefs = self.get_all_prefs()
        if not prefs:
            return ""
        lines = [f"- {k}: {v}" for k, v in prefs.items()]
        return "\n".join(lines)

    # --- Notes & Tasks ---
    def add_note(self, content: str, category: str = "note") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO notes (content, category, created_at) VALUES (?, ?, ?)",
                           (content, category, time.time()))
            conn.commit()
            return cursor.lastrowid

    def get_recent_notes(self, limit: int = 5) -> List[Dict[str, Any]]:
        notes = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, category, created_at FROM notes ORDER BY created_at DESC LIMIT ?", (limit,))
            for nid, content, cat, ts in cursor.fetchall():
                notes.append({"id": nid, "content": content, "category": cat, "created_at": ts})
        return notes


memory = MemoryManager()
