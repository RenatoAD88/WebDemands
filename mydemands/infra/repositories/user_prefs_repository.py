from __future__ import annotations

import json
from pathlib import Path

from mydemands.infra.paths import Paths


class UserPrefsRepository:
    def __init__(self, paths: Paths):
        self.paths = paths

    def _prefs_file(self, email: str) -> Path:
        user_dir = self.paths.ensure_user_dirs(email)
        return user_dir / "data" / "prefs.json"

    def load(self, email: str) -> dict:
        prefs_file = self._prefs_file(email)
        if not prefs_file.exists():
            return {"always_require_password_on_start": False, "theme": "light"}
        data = json.loads(prefs_file.read_text(encoding="utf-8"))
        return {
            "always_require_password_on_start": bool(data.get("always_require_password_on_start", False)),
            "theme": str(data.get("theme") or "light"),
        }

    def save(self, email: str, prefs: dict) -> None:
        prefs_file = self._prefs_file(email)
        payload = {
            "always_require_password_on_start": bool(prefs.get("always_require_password_on_start", False)),
            "theme": "dark" if str(prefs.get("theme") or "light").lower() == "dark" else "light",
        }
        temp_file = prefs_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(payload), encoding="utf-8")
        temp_file.replace(prefs_file)
