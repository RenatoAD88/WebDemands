from pathlib import Path

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", reason="PySide6 indisponível no ambiente de teste", exc_type=ImportError)

from mydemands.infra.repositories.last_login_repository import LastLoginRepository
from mydemands.infra.repositories.user_prefs_repository import UserPrefsRepository
from mydemands.ui.login_window import LoginWindow


class _DummyResetService:
    def start_reset(self, email: str) -> None:
        return None


QApplication = qtwidgets.QApplication


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_always_require_password_on_start_blocks_remember_mode(env, tmp_path: Path):
    _get_app()
    auth = env["auth"]
    paths = env["paths"]

    auth.register("user@test.com", "Abcdef1!")
    auth.create_remember_session("user@test.com", ttl_days=1)

    user_prefs = UserPrefsRepository(paths)
    user_prefs.save("user@test.com", {"always_require_password_on_start": True})
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")
    last_login.save_last_email("user@test.com")

    login = LoginWindow(auth, _DummyResetService(), lambda _email: None, user_prefs, last_login)

    assert login.password.isEnabled() is True
    assert login.remembered_user_email is None


def test_always_require_password_pref_persists_per_user(env):
    paths = env["paths"]
    prefs_repo = UserPrefsRepository(paths)

    prefs_repo.save("a@test.com", {"always_require_password_on_start": True})
    prefs_repo.save("b@test.com", {"always_require_password_on_start": False})

    assert prefs_repo.load("a@test.com")["always_require_password_on_start"] is True
    assert prefs_repo.load("b@test.com")["always_require_password_on_start"] is False


def test_toggle_always_require_password_updates_prefs(env):
    _get_app()
    paths = env["paths"]
    prefs_repo = UserPrefsRepository(paths)
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")
    last_login.save_last_email("user@test.com")

    login = LoginWindow(env["auth"], _DummyResetService(), lambda _email: None, prefs_repo, last_login)
    login.always_require_password_on_start.setChecked(True)

    saved = prefs_repo.load("user@test.com")
    assert saved["always_require_password_on_start"] is True


def test_last_email_saved_after_login(env):
    _get_app()
    auth = env["auth"]
    paths = env["paths"]

    auth.register("user@test.com", "Abcdef1!")
    prefs_repo = UserPrefsRepository(paths)
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")

    opened = {}

    def on_login(email: str):
        opened["email"] = email

    login = LoginWindow(auth, _DummyResetService(), on_login, prefs_repo, last_login)
    login.email.setText("user@test.com")
    login.password.setText("Abcdef1!")

    login._login()

    assert opened["email"] == "user@test.com"
    assert last_login.load_last_email() == "user@test.com"
