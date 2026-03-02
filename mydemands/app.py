from __future__ import annotations

import sys

import mydemands.resources_rc  # noqa: F401

from PySide6.QtWidgets import QApplication

from app import MainWindow
from csv_store import CsvStore
from mydemands.infra.db import Database
from mydemands.infra.paths import Paths
from mydemands.infra.repositories.session_repository import SessionRepository
from mydemands.infra.repositories.settings_repository import SettingsRepository
from mydemands.infra.repositories.user_repository import UserRepository
from mydemands.infra.secrets.dpapi_secret_store import WindowsDpapiSecretStore
from mydemands.services.auth_service import AuthService, MASTER_EMAIL
from mydemands.services.email_service import EmailService
from mydemands.services.password_reset_service import PasswordResetService
from mydemands.services.master_password_admin_service import MasterPasswordAdminService
from mydemands.services.user_context import UserContext, set_current_user
from mydemands.app_controller import AppController
from mydemands.ui.login_window import LoginWindow
from mydemands.infra.repositories.last_login_repository import LastLoginRepository
from mydemands.infra.repositories.user_prefs_repository import UserPrefsRepository
from mydemands.services.theme_service import ThemeService
from mydemands.services.secure_csv_exchange_service import SecureCsvExchangeService
from ui_theme import build_app_stylesheet


def main() -> int:
    qt_app = QApplication(sys.argv)

    qt_app.setStyleSheet(build_app_stylesheet("light"))

    paths = Paths()
    paths.ensure_base_dir()
    db = Database(paths)
    db.init_db()

    users = UserRepository(db)
    sessions = SessionRepository(paths.session_file)
    settings = SettingsRepository(paths.email_settings_file)
    secrets_store = WindowsDpapiSecretStore(paths.user_secrets_file(MASTER_EMAIL))
    auth = AuthService(users, sessions, secrets_store)
    auth.seed_master()

    email_service = EmailService(settings, secrets_store)
    reset_service = PasswordResetService(users, email_service)
    master_password_admin_service = MasterPasswordAdminService(users, email_service, reset_service)

    def _create_login_window() -> LoginWindow:
        login = LoginWindow(
            auth,
            reset_service,
            _open_main,
            user_prefs,
            last_login,
            on_authenticated=lambda: login.close(),
        )
        return login

    app_controller = AppController(auth, qt_app, _create_login_window)
    theme_service = ThemeService(qt_app)

    def _open_main(email: str):
        user = users.get_by_email(email)
        if user is None:
            return
        paths.migrate_legacy_data_for_user(email)
        user_dir = paths.ensure_user_dirs(email)
        context = UserContext(email=user.email, role=user.role, user_id=paths.user_id_from_email(user.email), user_dir=user_dir)
        set_current_user(context)
        store = CsvStore(str(paths.user_data_dir(email)))
        prefs = user_prefs.load(email)
        theme_service.apply_theme(str(prefs.get("theme") or "light"))
        win = MainWindow(
            store,
            logged_user_email=email,
            logged_user_role=user.role,
            email_service=email_service,
            password_reset_service=reset_service,
            master_password_admin_service=master_password_admin_service,
            backup_root=str(user_dir / "backups"),
            exports_root=str(user_dir / "exports"),
            on_logoff=app_controller.handle_logoff,
            user_prefs_repo=user_prefs,
            theme_service=theme_service,
            secure_csv_service=SecureCsvExchangeService(secrets_store),
        )
        win.resize(1280, 720)
        existing_win = getattr(qt_app, "_main_win", None)
        if existing_win is not None:
            existing_win.close()
            existing_win.deleteLater()
        app_controller.register_main_window(win)
        win.show()
        qt_app._main_win = win  # type: ignore[attr-defined]

    user_prefs = UserPrefsRepository(paths)
    last_login = LastLoginRepository(paths.base_dir / "last_login.json")

    login = _create_login_window()
    login.show()
    login.focus_first_field()

    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
