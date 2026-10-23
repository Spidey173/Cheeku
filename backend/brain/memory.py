import sqlite3
import os
import json
import time
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.models.schemas import ChatMessage, MessageRole
from backend.utils.logger import logger


class MemoryManager:
    """
    Session-aware Memory Manager for Cheeku AI.
    Isolates short-term conversation context per session while persisting
    long-term facts and notes safely.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(settings.DATA_DIR, "cheeku_memory.db")
        self._init_db()
        # Isolated short-term conversation memory per session ID
        self._session_histories: Dict[str, List[ChatMessage]] = {}

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check existing kv_memory schema to ensure composite primary key (session_id, key)
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='kv_memory'")
                row = cursor.fetchone()
                if row:
                    sql_text = row[0].upper()
                    if "PRIMARY KEY (SESSION_ID, KEY)" not in sql_text and "PRIMARY KEY(SESSION_ID, KEY)" not in sql_text:
                        logger.info("Migrating kv_memory schema to composite primary key (session_id, key)...")
                        cursor.execute("""
                            CREATE TABLE kv_memory_migrated (
                                session_id TEXT NOT NULL DEFAULT 'default',
                                key TEXT NOT NULL,
                                value TEXT NOT NULL,
                                category TEXT DEFAULT 'general',
                                updated_at REAL NOT NULL,
                                PRIMARY KEY (session_id, key)
                            )
                        """)
                        cursor.execute("PRAGMA table_info(kv_memory)")
                        old_cols = [r[1] for r in cursor.fetchall()]
                        if "session_id" in old_cols:
                            cursor.execute("INSERT OR REPLACE INTO kv_memory_migrated SELECT session_id, key, value, category, updated_at FROM kv_memory")
                        else:
                            cursor.execute("INSERT OR REPLACE INTO kv_memory_migrated SELECT 'default', key, value, category, updated_at FROM kv_memory")
                        cursor.execute("DROP TABLE kv_memory")
                        cursor.execute("ALTER TABLE kv_memory_migrated RENAME TO kv_memory")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS kv_memory (
                        session_id TEXT NOT NULL DEFAULT 'default',
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (session_id, key)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL DEFAULT 'default',
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL DEFAULT 'default',
                        content TEXT NOT NULL,
                        category TEXT DEFAULT 'note',
                        created_at REAL NOT NULL
                    )
                """)

                cursor.execute("PRAGMA table_info(conversation_history)")
                ch_cols = [r[1] for r in cursor.fetchall()]
                if "session_id" not in ch_cols:
                    cursor.execute("ALTER TABLE conversation_history ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'")

                cursor.execute("PRAGMA table_info(notes)")
                notes_cols = [r[1] for r in cursor.fetchall()]
                if "session_id" not in notes_cols:
                    cursor.execute("ALTER TABLE notes ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_session ON notes (session_id)")

                conn.commit()
                logger.info(f"Memory database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize memory database: {e}")

    # --- Short-term Memory (Strictly Isolated by Session) ---
    def add_short_term(
        self,
        role: MessageRole,
        content: str,
        session_id: str = "default",
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        name: Optional[str] = None
    ):
        if session_id not in self._session_histories:
            self._session_histories[session_id] = []

        history = self._session_histories[session_id]
        history.append(
            ChatMessage(
                role=role,
                content=content or "",
                tool_call_id=tool_call_id,
                tool_calls=tool_calls,
                name=name,
                timestamp=time.time()
            )
        )
        if len(history) > settings.MAX_HISTORY_TURNS * 2:
            self._session_histories[session_id] = history[-settings.MAX_HISTORY_TURNS * 2:]

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO conversation_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (session_id, role.value, content or "", time.time())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving to long-term conversation log: {e}")

    def get_short_term(self, session_id: str = "default") -> List[ChatMessage]:
        return list(self._session_histories.get(session_id, []))

    def clear_short_term(self, session_id: str = "default"):
        self._session_histories.pop(session_id, None)

    # --- Long-term Key-Value Memory (Partitioned by Session) ---
    def set_pref(self, key: str, value: Any, session_id: str = "default", category: str = "general"):
        try:
            val_str = json.dumps(value) if not isinstance(value, str) else value
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO kv_memory (session_id, key, value, category, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """, (session_id, key, val_str, category, time.time()))
                conn.commit()
            logger.info(f"[{session_id}] Memory updated: category='{category}', key='{key}'")
        except Exception as e:
            logger.error(f"Error writing to kv_memory: {e}")

    def get_pref(self, key: str, default: Any = None, session_id: str = "default") -> Any:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM kv_memory WHERE session_id = ? AND key = ?", (session_id, key))
                row = cursor.fetchone()
                if row:
                    try:
                        return json.loads(row[0])
                    except Exception:
                        return row[0]
        except Exception as e:
            logger.error(f"Error reading kv_memory: {e}")
        return default

    def get_all_prefs(self, session_id: str = "default") -> Dict[str, Any]:
        prefs = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM kv_memory WHERE session_id = ?", (session_id,))
                for k, v in cursor.fetchall():
                    try:
                        prefs[k] = json.loads(v)
                    except Exception:
                        prefs[k] = v
        except Exception as e:
            logger.error(f"Error fetching all prefs for session '{session_id}': {e}")
        return prefs

    def get_context_summary(self, session_id: str = "default") -> str:
        """Summarizes user profile and saved facts for this specific session to inject into system prompt."""
        prefs = self.get_all_prefs(session_id=session_id)
        if not prefs:
            return ""
        lines = [f"- {k}: {v}" for k, v in prefs.items()]
        return "\n".join(lines)

    # --- Notes & Tasks (Partitioned by Session) ---
    def add_note(self, content: str, session_id: str = "default", category: str = "note") -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (session_id, content, category, created_at) VALUES (?, ?, ?, ?)",
                (session_id, content, category, time.time())
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_notes(self, session_id: str = "default", limit: int = 5) -> List[Dict[str, Any]]:
        notes = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, content, category, created_at FROM notes WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit)
            )
            for nid, content, cat, ts in cursor.fetchall():
                notes.append({"id": nid, "content": content, "category": cat, "created_at": ts})
        return notes

    def clear_session_data(self, session_id: str):
        """Cleans up all session-specific records (history, preferences, and notes)."""
        self.clear_short_term(session_id)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM kv_memory WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM notes WHERE session_id = ?", (session_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error clearing data for session '{session_id}': {e}")


memory = MemoryManager()
