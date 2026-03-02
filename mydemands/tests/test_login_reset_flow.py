from datetime import datetime, timedelta

import pytest

qtwidgets = pytest.importorskip("PySide6.QtWidgets", reason="PySide6 indisponível no ambiente de teste", exc_type=ImportError)

from mydemands.domain.models import EmailSettings
from mydemands.infra.repositories.last_login_repository import LastLoginRepository
from mydemands.infra.repositories.user_prefs_repository import UserPrefsRepository
from mydemands.services.auth_service import InvalidCredentialsError
from mydemands.services.email_service import SMTP_PASSWORD_KEY
from mydemands.ui.login_window import LoginWindow

QApplication = qtwidgets.QApplication
QDialog = qtwidgets.QDialog


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _configure(env):
    env["settings"].save_email_settings(
        EmailSettings(
            smtp_host="smtp.test",
            smtp_port=587,
            use_tls=True,
            smtp_username="user",
            from_email="noreply@test.com",
            reply_to=None,
            subject_template="Recuperação",
            body_template="Senha provisória: {PASSWORD}. Expira em {MINUTOS} minutos. Verifique spam.",
        )
    )
    env["secrets"].set(SMTP_PASSWORD_KEY, b"secret")


def test_login_with_provisional_within_time_forces_reset_dialog(env, monkeypatch):
    _get_app()
    env["auth"].register("user@test.com", "Abcdef1!")
    _configure(env)
    monkeypatch.setattr(env["reset"], "_generate_provisional_password", lambda: "Prov_1234567890")
    env["reset"].request_password_reset("user@test.com")

    user = env["auth"].authenticate("user@test.com", "Prov_1234567890")
    assert user.auth_state == "requires_password_change"

    paths = env["paths"]
    prefs_repo = UserPrefsRepository(paths)
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")

    opened = {"reset_modal": False, "email": None}

    class _FakeResetDialog:
        def __init__(self, reset_service, email, parent=None):
            opened["reset_modal"] = True
            self.final_password = "Xyzabc1!"

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("mydemands.ui.login_window.ResetPasswordDialog", _FakeResetDialog)

    login = LoginWindow(env["auth"], env["reset"], lambda email: opened.__setitem__("email", email), prefs_repo, last_login)
    login.email.setText("user@test.com")
    login.password.setText("Prov_1234567890")
    login._login()

    assert opened["reset_modal"] is True
    assert opened["email"] == "user@test.com"


def test_login_with_expired_provisional_triggers_resend_and_blocks_login(env, monkeypatch):
    env["auth"].register("user@test.com", "Abcdef1!")
    _configure(env)
    monkeypatch.setattr(env["reset"], "_generate_provisional_password", lambda: "Prov_1234567890")
    env["reset"].request_password_reset("user@test.com")

    user = env["users"].get_by_email("user@test.com")
    assert user is not None
    user.provisional_expires_at = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    env["users"].update(user)

    with pytest.raises(InvalidCredentialsError, match="senha provisória expirou"):
        env["auth"].authenticate("user@test.com", "Prov_1234567890")

    assert env["reset"].auto_resend_expired_provisional("user@test.com") is True
    first_len = len(env["provider"].calls)
    assert first_len == 2
    assert env["reset"].auto_resend_expired_provisional("user@test.com") is False
    assert len(env["provider"].calls) == first_len


def test_loginwindow_clickable_label_opens_forgot_password(env, monkeypatch):
    _get_app()
    paths = env["paths"]
    prefs_repo = UserPrefsRepository(paths)
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")
    opened = {"called": False}

    class _FakeForgotDialog:
        def __init__(self, reset_service, parent=None):
            opened["called"] = True

        def exec(self):
            return QDialog.Accepted

    monkeypatch.setattr("mydemands.ui.login_window.ForgotPasswordDialog", _FakeForgotDialog)

    login = LoginWindow(env["auth"], env["reset"], lambda _email: None, prefs_repo, last_login)
    login.forgot_label.clicked.emit()
    assert opened["called"] is True
