from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Optional


class AIAuditLogger:
    def __init__(self, base_dir: str):
        self.path = os.path.join(base_dir, "ai_writing_audit.sqlite3")
        self._ensure_db()

    def _ensure_db(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    demand_id TEXT,
                    field_name TEXT,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    text_size INTEGER,
                    debug_text TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def log_event(
        self,
        event_type: str,
        demand_id: str,
        field_name: str,
        text: str,
        success: bool,
        error_message: Optional[str] = None,
        privacy_mode: bool = True,
        debug_mode: bool = False,
    ) -> None:
        debug_text = text if debug_mode and not privacy_mode else None
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO ai_events (event_type, demand_id, field_name, success, error_message, text_size, debug_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    demand_id,
                    field_name,
                    1 if success else 0,
                    (error_message or "")[:300],
                    len(text or ""),
                    debug_text,
                    datetime.utcnow().isoformat(),
                ),
            )
