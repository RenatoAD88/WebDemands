from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QApplication

from mydemands.ui.stylesheets import BASE_QSS, DARK_COLORS_QSS, LIGHT_COLORS_QSS


class ThemeService:
    def __init__(self, app: QApplication):
        self.app = app
        self._current = "light"
        self._listeners: list[Callable[[str], None]] = []

    def add_theme_listener(self, callback: Callable[[str], None]) -> None:
        self._listeners.append(callback)

    def apply_theme(self, theme_name: str) -> None:
        theme = (theme_name or "light").strip().lower()
        if theme not in {"light", "dark"}:
            theme = "light"
        stylesheet = BASE_QSS + "\n" + (DARK_COLORS_QSS if theme == "dark" else LIGHT_COLORS_QSS)
        app = QApplication.instance() or self.app
        app.setStyleSheet(stylesheet)
        self._current = theme
        for callback in list(self._listeners):
            callback(theme)

    def current_theme(self) -> str:
        return self._current
