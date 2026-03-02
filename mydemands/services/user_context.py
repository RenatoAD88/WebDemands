from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class UserContext:
    email: str
    role: str
    user_id: str
    user_dir: Path


_current_user: Optional[UserContext] = None


def set_current_user(user: UserContext | None) -> None:
    global _current_user
    _current_user = user


def current_user() -> Optional[UserContext]:
    return _current_user


def current_user_dir() -> Path | None:
    user = current_user()
    return user.user_dir if user else None


def clear() -> None:
    set_current_user(None)
