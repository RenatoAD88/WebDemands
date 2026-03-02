from __future__ import annotations

from datetime import datetime, time
from typing import Callable, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from .models import Notification, NotificationType
from .store import NotificationStore
from .center_table import (
    NotificationFilterProxy,
    NotificationTableModel,
    notification_column_index,
)


class NotificationCenterDialog(QDialog):
    def __init__(
        self,
        store: NotificationStore,
        on_open: Callable[[Notification], None],
        on_change: Optional[Callable[[], None]] = None,
        on_refresh_pending: Optional[Callable[[], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.on_open = on_open
        self.on_change = on_change
        self.on_refresh_pending = on_refresh_pending
        self.setWindowTitle("Central de Notificações")
        self.resize(900, 420)

        self.type_filter = QComboBox()
        self.type_filter.addItem("Todos", None)
        for nt in NotificationType:
            self.type_filter.addItem(nt.value, nt)
        self.type_filter.currentIndexChanged.connect(self.refresh)

        self.read_filter = QComboBox()
        self.read_filter.addItem("Todas", None)
        self.read_filter.addItem("Não lidas", False)
        self.read_filter.addItem("Lidas", True)
        self.read_filter.currentIndexChanged.connect(self._apply_read_filter)

        self.id_filter = QLineEdit()
        self.id_filter.setPlaceholderText("ID exato")
        self.keyword_filter = QLineEdit()
        self.keyword_filter.setPlaceholderText("Buscar palavra-chave")

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("dd/MM/yyyy")
        current_date = datetime.now().date()
        start_current_month = current_date.replace(day=1)
        self.date_start.setDate(start_current_month)
        self.date_start.dateChanged.connect(self._apply_date_filters)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("dd/MM/yyyy")
        self.date_end.setDate(current_date)
        self.date_end.dateChanged.connect(self._apply_date_filters)

        self.table_model = NotificationTableModel(self)
        self.proxy = NotificationFilterProxy(self)
        self.proxy.setSourceModel(self.table_model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSectionResizeMode(notification_column_index("body"), QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(notification_column_index("demand_id"), QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(notification_column_index("type"), QHeaderView.ResizeToContents)
        self.table.setColumnWidth(notification_column_index("demand_description"), 220)
        self.table.setColumnWidth(notification_column_index("timestamp"), 170)
        self.table.setColumnWidth(notification_column_index("title"), 220)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.selectionModel().selectionChanged.connect(self._update_mark_button_label)
        self.table.doubleClicked.connect(self._open_selected)

        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(250)
        self._filter_timer.timeout.connect(self._apply_text_filters)
        for widget in [self.id_filter, self.keyword_filter]:
            widget.textChanged.connect(self._schedule_filter_update)

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.setInterval(30000)
        self._auto_refresh_timer.timeout.connect(self.refresh_pending_notifications)
        self._auto_refresh_timer.start()

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Tipo"))
        filter_row.addWidget(self.type_filter)
        filter_row.addWidget(QLabel("Status"))
        filter_row.addWidget(self.read_filter)
        filter_row.addWidget(QLabel("ID"))
        filter_row.addWidget(self.id_filter)
        filter_row.addWidget(QLabel("Buscar palavra-chave"))
        filter_row.addWidget(self.keyword_filter)
        filter_row.addWidget(QLabel("Início"))
        filter_row.addWidget(self.date_start)
        filter_row.addWidget(QLabel("Fim"))
        filter_row.addWidget(self.date_end)
        clear_btn = QPushButton("Limpar filtros")
        clear_btn.clicked.connect(self.clear_filters)
        self.mark_toggle_btn = QPushButton("Marcar como lida")
        self.mark_toggle_btn.clicked.connect(self.toggle_selected_read_status)
        delete_btn = QPushButton("Excluir")
        delete_btn.clicked.connect(self.delete_selected_notifications)
        filter_row.addWidget(clear_btn)
        filter_row.addWidget(self.mark_toggle_btn)
        filter_row.addWidget(delete_btn)

        self.summary_label = QLabel()

        root = QVBoxLayout(self)
        root.addLayout(filter_row)
        root.addWidget(self.summary_label)
        root.addWidget(self.table)
        self.setLayout(root)
        self.refresh()

    def refresh(self) -> None:
        type_filter = self.type_filter.currentData()
        read_filter = self.read_filter.currentData()
        rows = self.store.list_notifications(type_filter=type_filter, read_filter=read_filter)
        self.table_model.set_notifications(rows)
        self.proxy.sort(notification_column_index("timestamp"), Qt.DescendingOrder)
        self._apply_text_filters()
        self._apply_date_filters()
        self._update_mark_button_label()
        self._update_summary()

    def _display_demand_id(self, n: Notification) -> str:
        raw_id = n.demand_id
        if raw_id in (None, ""):
            raw_id = (n.payload or {}).get("demand_id")
        text = str(raw_id or "").strip()
        return text or "—"

    def _display_demand_description(self, n: Notification) -> str:
        raw_description = n.demand_description
        if raw_description in (None, ""):
            raw_description = (n.payload or {}).get("demand_description")
        text = str(raw_description or "").strip()
        return text or "—"

    def _selected_notification_ids(self) -> list[int]:
        selected_ids: list[int] = []
        for idx in self.table.selectionModel().selectedRows():
            source_idx = self.proxy.mapToSource(idx)
            notification = self.table_model.notification_at(source_idx.row())
            if notification and notification.id:
                selected_ids.append(int(notification.id))
        return selected_ids

    def _selected_notification(self) -> Notification | None:
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return None
        source_idx = self.proxy.mapToSource(idxs[0])
        notification = self.table_model.notification_at(source_idx.row())
        if not notification or not notification.id:
            return None
        return self.store.get_notification_by_id(int(notification.id))

    def _update_mark_button_label(self) -> None:
        notification = self._selected_notification()
        if notification and notification.read:
            self.mark_toggle_btn.setText("Marcar como não lida")
        else:
            self.mark_toggle_btn.setText("Marcar como lida")

    def toggle_selected_read_status(self) -> None:
        selected = self._selected_notification()
        if selected is None:
            return
        ids = self._selected_notification_ids()
        if selected.read:
            for notif_id in ids:
                self.store.mark_as_unread(notif_id)
        else:
            for notif_id in ids:
                self.store.mark_as_read(notif_id)
        self.refresh()
        self._notify_change()

    def delete_selected_notifications(self) -> None:
        ids = self._selected_notification_ids()
        for notif_id in ids:
            self.store.delete_notification(notif_id)
        self.refresh()
        self._notify_change()

    def _open_selected(self, *_args):
        notification = self._selected_notification()
        if not notification:
            return
        demand_id = self._display_demand_id(notification)
        if demand_id == "—" and str(notification.payload.get("route") or "") != "atrasadas":
            QMessageBox.information(self, "Central de Notificações", "Notificação sem demanda vinculada")
            return
        self.store.mark_as_read(int(notification.id))
        self.on_open(notification)
        self.refresh()
        self._notify_change()

    def refresh_pending_notifications(self) -> None:
        if self.on_refresh_pending:
            self.on_refresh_pending()
        self.refresh()
        self._notify_change()

    def _notify_change(self) -> None:
        if self.on_change:
            self.on_change()

    def _schedule_filter_update(self) -> None:
        self._filter_timer.start()

    def _apply_text_filters(self) -> None:
        self.proxy.set_filter_value("demand_id", self.id_filter.text())
        self.proxy.set_filter_value("keyword", self.keyword_filter.text())
        self._update_summary()

    def _apply_read_filter(self) -> None:
        self.proxy.set_filter_value("read", self.read_filter.currentData())
        self._update_summary()

    def _apply_date_filters(self) -> None:
        start_dt = datetime.combine(self.date_start.date().toPython(), time.min)
        end_dt = datetime.combine(self.date_end.date().toPython(), time.max)
        self.proxy.set_filter_value("timestamp_start", start_dt)
        self.proxy.set_filter_value("timestamp_end", end_dt)
        self._update_summary()

    def clear_filters(self) -> None:
        self.type_filter.setCurrentIndex(0)
        self.read_filter.setCurrentIndex(0)
        self.id_filter.clear()
        self.keyword_filter.clear()
        current_date = datetime.now().date()
        self.date_start.setDate(current_date.replace(day=1))
        self.date_end.setDate(current_date)
        self.proxy.clear_filters()
        self._apply_date_filters()
        self._update_summary()

    def _update_summary(self) -> None:
        total = self.table_model.rowCount()
        filtered = self.proxy.rowCount()
        self.summary_label.setText(f"{total} notificações ({filtered} filtradas)")
