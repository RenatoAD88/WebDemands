from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class SessionRepository:
    def __init__(self, session_file: Path):
        self.session_file = session_file

    def save_session(self, email: str, token_protected: str, expires_at: datetime) -> None:
        payload = {
            "email": email.lower(),
            "token_protected": token_protected,
            "expires_at": expires_at.isoformat(),
        }
        self.session_file.write_text(json.dumps(payload), encoding="utf-8")

    def load_session(self) -> Optional[dict]:
        if not self.session_file.exists():
            return None
        data = json.loads(self.session_file.read_text(encoding="utf-8"))
        if datetime.fromisoformat(data["expires_at"]) < datetime.utcnow():
            self.clear_session()
            return None
        return data

    def clear_session(self) -> None:
        if self.session_file.exists():
            self.session_file.unlink()
