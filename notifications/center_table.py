from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, Qt

from .models import Notification


@dataclass(frozen=True)
class NotificationColumn:
    key: str
    header: str


NOTIFICATION_COLUMNS: tuple[NotificationColumn, ...] = (
    NotificationColumn("demand_id", "ID"),
    NotificationColumn("demand_description", "Descrição da demanda"),
    NotificationColumn("timestamp", "Data notificação"),
    NotificationColumn("type", "Tag"),
    NotificationColumn("title", "Observação"),
    NotificationColumn("body", "Mensagem"),
    NotificationColumn("read", "Status"),
)


def notification_column_index(column_key: str) -> int:
    for index, column in enumerate(NOTIFICATION_COLUMNS):
        if column.key == column_key:
            return index
    raise ValueError(f"Coluna não suportada: {column_key}")


class NotificationTableModel(QAbstractTableModel):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._rows: list[Notification] = []

    def set_notifications(self, rows: list[Notification]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def notification_at(self, row: int) -> Notification | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(NOTIFICATION_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(NOTIFICATION_COLUMNS):
            return NOTIFICATION_COLUMNS[section].header
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        notification = self._rows[index.row()]
        column_key = NOTIFICATION_COLUMNS[index.column()].key
        if role == Qt.UserRole:
            return self._sort_value(notification, column_key)
        if role == Qt.DisplayRole:
            return self._display_value(notification, column_key)
        if role == Qt.ToolTipRole and column_key == "demand_description":
            return self._safe_text(self._demand_description(notification), placeholder="—")
        if role == Qt.TextAlignmentRole and column_key in {"demand_id", "timestamp", "type"}:
            return int(Qt.AlignHCenter | Qt.AlignVCenter)
        if role == Qt.TextAlignmentRole and column_key == "demand_description":
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        return None

    def _display_value(self, notification: Notification, column_key: str) -> str:
        if column_key == "timestamp":
            return notification.timestamp.strftime("%d/%m/%Y %H:%M")
        if column_key == "type":
            return notification.type.value
        if column_key == "title":
            return self._safe_text(notification.title)
        if column_key == "demand_id":
            return self._safe_text(self._demand_id(notification), placeholder="—")
        if column_key == "demand_description":
            return self._safe_text(self._demand_description(notification), placeholder="—")
        if column_key == "body":
            return self._safe_text(notification.body)
        if column_key == "read":
            return "Lida" if notification.read else "Não lida"
        return ""

    def _sort_value(self, notification: Notification, column_key: str) -> Any:
        if column_key == "timestamp":
            return int(notification.timestamp.timestamp())
        if column_key == "demand_id":
            demand_id = self._demand_id(notification)
            try:
                return int(str(demand_id).strip())
            except (TypeError, ValueError):
                return -1
        if column_key == "read":
            return 1 if notification.read else 0
        return self._display_value(notification, column_key).lower()

    def _safe_text(self, value: Any, *, placeholder: str = "") -> str:
        text = str(value or "").strip()
        return text or placeholder

    def _demand_id(self, notification: Notification) -> str:
        raw_id = notification.demand_id
        if raw_id in (None, ""):
            raw_id = (notification.payload or {}).get("demand_id")
        return str(raw_id or "").strip()

    def _demand_description(self, notification: Notification) -> str:
        raw_desc = notification.demand_description
        if raw_desc in (None, ""):
            raw_desc = (notification.payload or {}).get("demand_description")
        return str(raw_desc or "").strip()


class NotificationFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._filters: dict[str, Any] = {}
        self.setSortRole(Qt.UserRole)

    def set_filter_value(self, column_key: str, value: Any) -> None:
        self._filters[column_key] = value
        self.invalidateFilter()

    def clear_filters(self) -> None:
        self._filters.clear()
        self.invalidateFilter()

    def active_filters(self) -> dict[str, Any]:
        return dict(self._filters)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        model = self.sourceModel()
        if not isinstance(model, NotificationTableModel):
            return True
        notification = model.notification_at(source_row)
        if notification is None:
            return False

        text_filters = {
            "type": model._display_value(notification, "type"),
        }
        for key, text in text_filters.items():
            needle = str(self._filters.get(key) or "").strip().lower()
            if needle and needle not in str(text or "").lower():
                return False

        keyword = str(self._filters.get("keyword") or "").strip().lower()
        if keyword:
            searchable_fields = [
                model._display_value(notification, "demand_description"),
                model._display_value(notification, "body"),
            ]
            haystack = " ".join(str(field or "").lower() for field in searchable_fields)
            if keyword not in haystack:
                return False

        demand_id_filter = self._filters.get("demand_id")
        if demand_id_filter not in (None, ""):
            try:
                expected = int(demand_id_filter)
            except (TypeError, ValueError):
                return False
            try:
                current = int(model._demand_id(notification))
            except (TypeError, ValueError):
                current = -1
            if current != expected:
                return False

        read_filter = self._filters.get("read")
        if read_filter is not None and bool(notification.read) != bool(read_filter):
            return False

        start_dt: datetime | None = self._filters.get("timestamp_start")
        end_dt: datetime | None = self._filters.get("timestamp_end")
        current_dt = notification.timestamp
        if current_dt.tzinfo is not None:
            current_dt = current_dt.replace(tzinfo=None)
        if start_dt and current_dt < start_dt:
            return False
        if end_dt and current_dt > end_dt:
            return False

        return True
