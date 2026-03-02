from __future__ import annotations

from typing import Dict

import mydemands.resources_rc  # noqa: F401

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QStyle


class IconService:
    ICON_SIZE = QSize(24, 24)

    _ICON_FILES: Dict[str, Dict[str, str]] = {
        "new_demand": {"light": ":/icons/new_demand_light.svg", "dark": ":/icons/new_demand_dark.svg"},
        "delete": {"light": ":/icons/delete_light.svg", "dark": ":/icons/delete_dark.svg"},
        "export": {"light": ":/icons/import_light.svg", "dark": ":/icons/import_dark.svg"},
        "import": {"light": ":/icons/export_light.svg", "dark": ":/icons/export_dark.svg"},
    }

    _FALLBACKS = {
        "new_demand": QStyle.SP_FileDialogNewFolder,
        "delete": QStyle.SP_TrashIcon,
        "export": QStyle.SP_ArrowUp,
        "import": QStyle.SP_ArrowDown,
    }

    def icon_size(self, _theme: str) -> QSize:
        return QSize(self.ICON_SIZE)

    def get_icon(self, name: str, theme: str) -> QIcon:
        normalized_theme = "dark" if (theme or "").strip().lower() == "dark" else "light"
        by_theme = self._ICON_FILES.get(name, {})
        icon_path = by_theme.get(normalized_theme) or by_theme.get("light")
        return QIcon(icon_path) if icon_path else QIcon()

    def fallback_for(self, name: str) -> QStyle.StandardPixmap:
        return self._FALLBACKS.get(name, QStyle.SP_FileIcon)
