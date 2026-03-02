from __future__ import annotations

import json
from pathlib import Path


class LastLoginRepository:
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def save_last_email(self, email: str) -> None:
        payload = {"last_email": (email or "").strip().lower()}
        temp_file = self.file_path.with_suffix(".tmp")
        temp_file.write_text(json.dumps(payload), encoding="utf-8")
        temp_file.replace(self.file_path)

    def load_last_email(self) -> str | None:
        if not self.file_path.exists():
            return None
        data = json.loads(self.file_path.read_text(encoding="utf-8"))
        email = str(data.get("last_email", "") or "").strip().lower()
        return email or None
