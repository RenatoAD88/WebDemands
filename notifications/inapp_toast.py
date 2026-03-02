from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLabel, QWidget


class InAppToast(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.label = QLabel(self)
        self.label.setStyleSheet(
            "background-color:#1f2937;color:white;border-radius:8px;padding:10px;font-size:12px;"
        )
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_toast(self, title: str, body: str, duration_ms: int = 3500) -> None:
        self.label.setText(f"<b>{title}</b><br>{body}")
        self.label.adjustSize()
        self.resize(self.label.size())
        parent = self.parentWidget()
        if parent:
            px = max(16, parent.width() - self.width() - 24)
            py = 24
            self.move(px, py)
        self.show()
        self.raise_()
        self._timer.start(duration_ms)


class InAppToastNotifier:
    def __init__(self, host: QWidget):
        self.toast = InAppToast(host)

    def notify(self, title: str, body: str) -> None:
        self.toast.show_toast(title, body)
