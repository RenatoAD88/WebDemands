import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from mydemands.infra.db import Database
from mydemands.infra.paths import Paths
from mydemands.infra.repositories.session_repository import SessionRepository
from mydemands.infra.repositories.settings_repository import SettingsRepository
from mydemands.infra.repositories.user_repository import UserRepository
from mydemands.infra.secrets.fake_secret_store import FakeSecretStore
from mydemands.services.auth_service import AuthService
from mydemands.services.email_service import EmailService
from mydemands.services.password_reset_service import PasswordResetService


class MockEmailProvider:
    def __init__(self):
        self.calls = []

    def send(self, **kwargs):
        self.calls.append(kwargs)


@pytest.fixture
def env(tmp_path: Path):
    paths = Paths(tmp_path)
    paths.ensure_base_dir()
    db = Database(paths)
    db.init_db()

    users = UserRepository(db)
    sessions = SessionRepository(paths.session_file)
    settings = SettingsRepository(paths.email_settings_file)
    secrets = FakeSecretStore()
    provider = MockEmailProvider()
    email = EmailService(settings, secrets, provider=provider)
    auth = AuthService(users, sessions, secrets)
    reset = PasswordResetService(users, email)
    return {
        "paths": paths,
        "db": db,
        "users": users,
        "sessions": sessions,
        "settings": settings,
        "secrets": secrets,
        "provider": provider,
        "email": email,
        "auth": auth,
        "reset": reset,
    }
