from __future__ import annotations

from dataclasses import dataclass

from mydemands.services.auth_service import AuthService


@dataclass(frozen=True)
class StartupDecision:
    state: str
    user_email: str | None = None


def resolve_startup_decision(auth: AuthService) -> StartupDecision:
    remembered_user = auth.try_auto_login()
    if remembered_user:
        return StartupDecision(state="confirm_remember", user_email=remembered_user.email)
    return StartupDecision(state="login")
