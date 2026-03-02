from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class User:
    email: str
    password_hash: str
    role: str = "default"
    must_change_password: bool = False
    provisional_expires_at: Optional[str] = None
    provisional_issued_at: Optional[str] = None
    auth_state: str = "authenticated"


@dataclass(slots=True)
class ResetToken:
    email: str
    token_hash: str
    expires_at: datetime
    used: bool = False
    created_at: Optional[datetime] = None


@dataclass(slots=True)
class EmailSettings:
    smtp_host: str
    smtp_port: int
    use_tls: bool
    smtp_username: str
    from_email: str
    reply_to: Optional[str]
    subject_template: str
    body_template: str
