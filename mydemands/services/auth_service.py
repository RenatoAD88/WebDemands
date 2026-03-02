from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta

try:
    import bcrypt  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - fallback path covered in tests via monkeypatch
    bcrypt = None

from mydemands.domain.models import User
from mydemands.domain.password_policy import PasswordPolicy
from mydemands.infra.repositories.session_repository import SessionRepository
from mydemands.infra.repositories.user_repository import UserRepository
from mydemands.infra.secrets.secret_store import ISecretStore

MASTER_EMAIL = "renatoaugustod@gmail.com"
MASTER_PASSWORD = "DANRe102023@@mydemands"
REMEMBER_KEY = "remember_token"
PBKDF2_PREFIX = "pbkdf2_sha256$"


class AuthError(Exception):
    pass


class DuplicateEmailError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


def hash_password(password: str) -> str:
    if bcrypt is not None:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 390000)
    return f"{PBKDF2_PREFIX}{salt}${digest.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        if hashed.startswith(PBKDF2_PREFIX):
            _, salt, expected_hex = hashed.split("$", 2)
            digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 390000)
            return secrets.compare_digest(digest.hex(), expected_hex)
        if bcrypt is None:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


class AuthService:
    EXPIRED_PROVISIONAL_MESSAGE = (
        "Sua senha provisória expirou. Enviamos uma nova senha provisória para o seu e-mail. "
        "Verifique também a caixa de spam."
    )

    def __init__(self, users: UserRepository, sessions: SessionRepository, secrets_store: ISecretStore):
        self.users = users
        self.sessions = sessions
        self.secrets_store = secrets_store
        self._cached_user: User | None = None

    def seed_master(self) -> None:
        if self.users.exists(MASTER_EMAIL):
            return
        self.users.add(User(email=MASTER_EMAIL, password_hash=hash_password(MASTER_PASSWORD), role="master", must_change_password=False))

    def register(self, email: str, password: str) -> User:
        normalized = email.strip().lower()
        ok, errors = PasswordPolicy.validate(password)
        if not ok:
            raise AuthError("; ".join(errors))
        if self.users.exists(normalized):
            raise DuplicateEmailError("E-mail já cadastrado")
        user = User(email=normalized, password_hash=hash_password(password), role="default", must_change_password=False)
        self.users.add(user)
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if not user:
            raise InvalidCredentialsError("Credenciais inválidas")

        if not verify_password(password, user.password_hash):
            if user.must_change_password and user.provisional_expires_at:
                try:
                    if datetime.utcnow() > datetime.fromisoformat(user.provisional_expires_at):
                        raise InvalidCredentialsError(self.EXPIRED_PROVISIONAL_MESSAGE)
                except ValueError:
                    pass
            raise InvalidCredentialsError("Credenciais inválidas")

        if user.must_change_password and user.provisional_expires_at:
            try:
                if datetime.utcnow() > datetime.fromisoformat(user.provisional_expires_at):
                    raise InvalidCredentialsError(self.EXPIRED_PROVISIONAL_MESSAGE)
            except ValueError:
                pass
            user.auth_state = "requires_password_change"
        else:
            user.auth_state = "authenticated"

        self._cached_user = user
        return user

    def create_remember_session(self, user_email: str, ttl_days: int = 7) -> None:
        token = secrets.token_urlsafe(32)
        protected = base64.b64encode(token.encode("utf-8")).decode("ascii")
        self.secrets_store.set(REMEMBER_KEY, token.encode("utf-8"))
        self.sessions.save_session(user_email, protected, datetime.utcnow() + timedelta(days=ttl_days))

    def clear_remember_session(self) -> None:
        self.sessions.clear_session()
        self.secrets_store.delete(REMEMBER_KEY)

    def try_auto_login(self) -> User | None:
        session = self.sessions.load_session()
        if not session:
            return None
        email = session["email"]
        protected = session.get("token_protected", "")
        try:
            presented_token = base64.b64decode(protected).decode("utf-8")
        except Exception:
            self.logout()
            return None
        expected_token = self.secrets_store.get(REMEMBER_KEY)
        if not expected_token:
            self.logout()
            return None
        if not hashlib.sha256(presented_token.encode()).digest() == hashlib.sha256(expected_token).digest():
            self.logout()
            return None
        self._cached_user = self.users.get_by_email(email)
        return self._cached_user

    def logout(self) -> None:
        self._cached_user = None
        self.clear_remember_session()
