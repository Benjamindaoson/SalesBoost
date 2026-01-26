import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from app.services.memory.storage import MemoryEntry, MemoryStorage, UserProfile

logger = logging.getLogger(__name__)


class SqliteMemoryStorage(MemoryStorage):
    """SQLite-backed memory storage."""

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_profiles (
                    user_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    skill_levels TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (user_id, tenant_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    session_id TEXT,
                    metadata TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_entries_user ON memory_entries (user_id, tenant_id)"
            )
            conn.commit()

    def load_profile(self, user_id: str, tenant_id: str = "public") -> Optional[UserProfile]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT skill_levels, updated_at FROM memory_profiles WHERE user_id = ? AND tenant_id = ?",
                (user_id, tenant_id),
            ).fetchone()
        if not row:
            return None
        skill_levels = json.loads(row[0]) if row[0] else {}
        return UserProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            skill_levels=skill_levels,
            updated_at=row[1] or "",
        )

    def save_profile(self, profile: UserProfile) -> None:
        payload = json.dumps(profile.skill_levels, ensure_ascii=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory_profiles (user_id, tenant_id, skill_levels, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, tenant_id) DO UPDATE SET
                    skill_levels=excluded.skill_levels,
                    updated_at=excluded.updated_at
                """,
                (profile.user_id, profile.tenant_id, payload, profile.updated_at),
            )
            conn.commit()

    def load_memories(self, user_id: str, tenant_id: str = "public") -> List[MemoryEntry]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, content, category, session_id, metadata, created_at
                FROM memory_entries
                WHERE user_id = ? AND tenant_id = ?
                ORDER BY created_at ASC
                """,
                (user_id, tenant_id),
            ).fetchall()
        memories = []
        for row in rows:
            metadata = json.loads(row[4]) if row[4] else {}
            memories.append(
                MemoryEntry(
                    id=row[0],
                    content=row[1],
                    category=row[2],
                    session_id=row[3],
                    metadata=metadata,
                    created_at=row[5] or "",
                )
            )
        return memories

    def save_memories(self, user_id: str, memories: List[MemoryEntry], tenant_id: str = "public") -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM memory_entries WHERE user_id = ? AND tenant_id = ?",
                (user_id, tenant_id),
            )
            for memory in memories:
                conn.execute(
                    """
                    INSERT INTO memory_entries (
                        id, user_id, tenant_id, content, category, session_id, metadata, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory.id,
                        user_id,
                        tenant_id,
                        memory.content,
                        memory.category,
                        memory.session_id,
                        json.dumps(memory.metadata, ensure_ascii=True),
                        memory.created_at,
                    ),
                )
            conn.commit()

