from __future__ import annotations

from datetime import datetime, timedelta

from mydemands.domain.models import User
from mydemands.infra.repositories.user_repository import UserRepository
from mydemands.services.auth_service import hash_password
from mydemands.services.email_service import EmailService, PROVISIONAL_MINUTES
from mydemands.services.password_reset_service import PasswordResetService


class MasterPasswordAdminService:
    def __init__(self, users: UserRepository, email_service: EmailService, reset_service: PasswordResetService):
        self.users = users
        self.email_service = email_service
        self.reset_service = reset_service

    def list_users(self) -> list[User]:
        return self.users.list_users()

    def send_new_password(self, email: str) -> str:
        normalized = (email or "").strip().lower()
        settings = self.email_service.load_settings()
        if not settings:
            raise RuntimeError("SMTP_NOT_CONFIGURED")
        self.email_service.get_smtp_password_for_send()

        now = datetime.utcnow()
        if not self.reset_service._allow_hourly_request(normalized, now):
            raise RuntimeError("RATE_LIMIT")

        user = self.users.get_by_email(normalized)
        if user is None:
            raise RuntimeError("USER_NOT_FOUND")

        provisional_password = self.reset_service._generate_provisional_password()
        user.password_hash = hash_password(provisional_password)
        user.must_change_password = True
        user.provisional_issued_at = now.isoformat()
        user.provisional_expires_at = (now + timedelta(minutes=PROVISIONAL_MINUTES)).isoformat()
        self.users.update(user)

        self.email_service.send_recovery_email(normalized, provisional_password)
        return "Senha provisória enviada com sucesso"
