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
QLineEdit = qtwidgets.QLineEdit


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_password_toggle_changes_echo_mode(env, tmp_path: Path):
    _get_app()
    paths = env["paths"]
    prefs_repo = UserPrefsRepository(paths)
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")

    login = LoginWindow(env["auth"], _DummyResetService(), lambda _email: None, prefs_repo, last_login)

    assert login.password.echoMode() == QLineEdit.Password

    login.password_toggle_action.trigger()
    assert login.password.echoMode() == QLineEdit.Normal

    login.password_toggle_action.trigger()
    assert login.password.echoMode() == QLineEdit.Password


def test_password_toggle_disabled_in_remembered_mode(env, tmp_path: Path):
    _get_app()
    auth = env["auth"]
    auth.register("user@test.com", "Abcdef1!")
    auth.create_remember_session("user@test.com", ttl_days=1)

    paths = env["paths"]
    prefs_repo = UserPrefsRepository(paths)
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")

    login = LoginWindow(auth, _DummyResetService(), lambda _email: None, prefs_repo, last_login)

    assert login.password.isEnabled() is False
    assert login.password_toggle_action.isEnabled() is False
    assert login.password.echoMode() == QLineEdit.Password
