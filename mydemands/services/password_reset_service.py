from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta

from mydemands.domain.password_policy import PasswordPolicy
from mydemands.infra.repositories.user_repository import UserRepository
from mydemands.services.auth_service import hash_password
from mydemands.services.email_service import EmailService, PROVISIONAL_MINUTES


class PasswordResetError(Exception):
    pass


class PasswordResetService:
    NEUTRAL_MESSAGE = (
        "Se houver uma conta com este e-mail, enviamos uma senha provisória. "
        "Verifique também a caixa de spam."
    )
    EXPIRED_MESSAGE = (
        "Sua senha provisória expirou. Enviamos uma nova senha provisória para o seu e-mail. "
        "Verifique também a caixa de spam."
    )

    def __init__(self, users: UserRepository, email_service: EmailService):
        self.users = users
        self.email_service = email_service
        self._requests_by_email: dict[str, list[datetime]] = defaultdict(list)
        self._auto_resend_by_email: dict[str, datetime] = {}

    @staticmethod
    def _norm(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _generate_provisional_password() -> str:
        return "Prov_" + "".join(str(random.randint(0, 9)) for _ in range(10))

    @staticmethod
    def _iso_now() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    def _allow_hourly_request(self, email: str, now: datetime) -> bool:
        requests = [t for t in self._requests_by_email[email] if (now - t) <= timedelta(hours=1)]
        self._requests_by_email[email] = requests
        if len(requests) >= 5:
            return False
        self._requests_by_email[email].append(now)
        return True

    def _issue_provisional_password(self, normalized: str, now: datetime) -> bool:
        if not self._allow_hourly_request(normalized, now):
            return False
        user = self.users.get_by_email(normalized)
        if not user:
            return True
        provisional_password = self._generate_provisional_password()
        user.password_hash = hash_password(provisional_password)
        user.must_change_password = True
        user.provisional_issued_at = now.isoformat()
        user.provisional_expires_at = (now + timedelta(minutes=PROVISIONAL_MINUTES)).isoformat()
        self.users.update(user)
        self.email_service.send_recovery_email(normalized, provisional_password)
        return True

    def request_password_reset(self, email: str) -> str:
        normalized = self._norm(email)
        now = datetime.utcnow()
        settings = self.email_service.load_settings()
        if not settings:
            raise RuntimeError("SMTP_NOT_CONFIGURED")
        self.email_service.get_smtp_password_for_send()

        self._issue_provisional_password(normalized, now)
        return self.NEUTRAL_MESSAGE

    def auto_resend_expired_provisional(self, email: str, cooldown_seconds: int = 60) -> bool:
        normalized = self._norm(email)
        now = datetime.utcnow()
        last_auto = self._auto_resend_by_email.get(normalized)
        if last_auto and (now - last_auto).total_seconds() < cooldown_seconds:
            return False
        sent = self._issue_provisional_password(normalized, now)
        if sent:
            self._auto_resend_by_email[normalized] = now
        return sent

    def save_final_password(self, email: str, new_password: str) -> None:
        normalized = self._norm(email)
        ok, errors = PasswordPolicy.validate(new_password)
        if not ok:
            raise PasswordResetError("; ".join(errors))

        user = self.users.get_by_email(normalized)
        if not user:
            raise PasswordResetError("Usuário não encontrado")

        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.provisional_expires_at = None
        user.provisional_issued_at = None
        self.users.update(user)

    def provisional_expired(self, email: str) -> bool:
        user = self.users.get_by_email(self._norm(email))
        if not user or not user.must_change_password:
            return False
        expires_at = self._parse_iso(user.provisional_expires_at)
        return bool(expires_at and datetime.utcnow() > expires_at)
