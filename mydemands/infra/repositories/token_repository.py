from __future__ import annotations

from datetime import datetime

from mydemands.infra.db import Database


class ResetTokenRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat()

    def add(self, email: str, token_hash: str, expires_at: datetime, used: int = 0) -> None:
        now = datetime.utcnow().isoformat()
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO reset_tokens(email,token_hash,expires_at,used,created_at) VALUES (?,?,?,?,?)",
                (email.lower(), token_hash, self._iso(expires_at), int(used), now),
            )
            conn.commit()

    def get_valid(self, email: str, token_hash: str, now: datetime):
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT email,token_hash,expires_at,used,created_at
                FROM reset_tokens
                WHERE email = ? AND token_hash = ? AND used = 0
                """,
                (email.lower(), token_hash),
            ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < now:
            return None
        return row

    def mark_used(self, email: str, token_hash: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE reset_tokens SET used = 1 WHERE email = ? AND token_hash = ?",
                (email.lower(), token_hash),
            )
            conn.commit()
