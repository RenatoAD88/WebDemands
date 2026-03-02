from __future__ import annotations

import hashlib
import re
from pathlib import Path


DEFAULT_BASE_DIR = Path(r"C:\MyDemands\masterData")


def ensure_base_dir(base_dir: Path | str | None = None) -> Path:
    return Paths(base_dir).ensure_base_dir()


def normalize_email(email: str) -> str:
    return Paths.normalize_email(email)


def user_id_from_email(email: str) -> str:
    return Paths.user_id_from_email(email)


def get_user_dir(email: str, base_dir: Path | str | None = None) -> Path:
    return Paths(base_dir).get_user_dir(email)


def ensure_user_dirs(email: str, base_dir: Path | str | None = None) -> Path:
    return Paths(base_dir).ensure_user_dirs(email)


class Paths:
    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_BASE_DIR

    def ensure_base_dir(self) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "users").mkdir(parents=True, exist_ok=True)
        return self.base_dir

    @staticmethod
    def normalize_email(email: str) -> str:
        return (email or "").strip().lower()

    @classmethod
    def user_id_from_email(cls, email: str) -> str:
        normalized = cls.normalize_email(email)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def get_user_dir(self, email: str) -> Path:
        return self.base_dir / "users" / self.user_id_from_email(email)

    def ensure_user_dirs(self, email: str) -> Path:
        user_dir = self.get_user_dir(email)
        for child in ("data", "db", "backups", "exports"):
            (user_dir / child).mkdir(parents=True, exist_ok=True)
        return user_dir

    def user_data_dir(self, email: str) -> Path:
        return self.ensure_user_dirs(email) / "data"

    def user_secrets_file(self, email: str) -> Path:
        return self.ensure_user_dirs(email) / "secrets.dat"

    def migrate_legacy_data_for_user(self, email: str) -> None:
        self.ensure_base_dir()
        user_data = self.user_data_dir(email)
        legacy_dir = self.base_dir / "legacy"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        excluded = {
            "users",
            "legacy",
            "auth.db",
            "users.db",
            "session.json",
            "email_settings.json",
            "secrets.dat",
        }
        for entry in self.base_dir.iterdir():
            if entry.name in excluded:
                continue
            if entry.is_dir():
                continue
            if re.match(r"^mydemands_.*\.db$", entry.name):
                continue
            target = user_data / entry.name
            if not target.exists():
                target.write_bytes(entry.read_bytes())
            backup_target = legacy_dir / entry.name
            if not backup_target.exists():
                backup_target.write_bytes(entry.read_bytes())

    @property
    def users_db(self) -> Path:
        legacy = self.base_dir / "users.db"
        return legacy if legacy.exists() else self.base_dir / "auth.db"

    @property
    def session_file(self) -> Path:
        return self.base_dir / "session.json"

    @property
    def email_settings_file(self) -> Path:
        return self.base_dir / "email_settings.json"

    @property
    def secrets_file(self) -> Path:
        return self.base_dir / "secrets.dat"
