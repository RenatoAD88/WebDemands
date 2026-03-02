from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon

LOGGER = logging.getLogger(__name__)


class SystemNotifier:
    def __init__(self, tray_icon: Optional[QSystemTrayIcon] = None):
        self.tray_icon = tray_icon

    def notify(self, title: str, body: str, icon: Optional[QIcon] = None) -> None:
        if self.tray_icon and self.tray_icon.isVisible():
            if icon is not None:
                self.tray_icon.setIcon(icon)
            self.tray_icon.showMessage(title, body, QSystemTrayIcon.Information, 6000)
            return
        LOGGER.info("System notification fallback: %s - %s", title, body)
