from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from mydemands.dashboard.demandas_schema_registry import DemandColumnSchema


class ColumnConfigDialog(QDialog):
    def __init__(self, schema: List[DemandColumnSchema], selected_ids: List[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurar colunas")
        self.resize(420, 520)
        self._schema = list(schema)
        self._selected_ids = set(selected_ids)

        layout = QVBoxLayout(self)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Buscar coluna")
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        actions = QHBoxLayout()
        btn_all = QPushButton("Selecionar tudo")
        btn_all.clicked.connect(self._select_all)
        btn_clear = QPushButton("Limpar")
        btn_clear.clicked.connect(self._clear_min_one)
        self.btn_restore = QPushButton("Restaurar padrão")
        self.btn_restore.clicked.connect(self.reject)
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        for btn in (btn_all, btn_clear, self.btn_restore, btn_close):
            actions.addWidget(btn)
        layout.addLayout(actions)
        self._populate()

    def _populate(self) -> None:
        self.list_widget.clear()
        for col in self._schema:
            item = QListWidgetItem(col.label)
            item.setData(Qt.UserRole, col.id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if col.id in self._selected_ids else Qt.Unchecked)
            self.list_widget.addItem(item)

    def _apply_filter(self, text: str) -> None:
        needle = (text or "").strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(needle not in item.text().lower())

    def _select_all(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)

    def _clear_min_one(self) -> None:
        first = True
        for i in range(self.list_widget.count()):
            state = Qt.Checked if first else Qt.Unchecked
            self.list_widget.item(i).setCheckState(state)
            first = False

    def selected_column_ids(self) -> List[str]:
        ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(str(item.data(Qt.UserRole)))
        return ids or ["id"]


class BaseGridView(QTableWidget):
    preferences_changed = Signal(dict)
    LEFT_ALIGNED_COLUMN_IDS = {"descricao", "comentario"}

    def __init__(self, schema: List[DemandColumnSchema], parent=None) -> None:
        super().__init__(0, len(schema), parent)
        self._schema = list(schema)
        self._id_to_index: Dict[str, int] = {c.id: idx for idx, c in enumerate(self._schema)}
        self._restoring = False

        self.setHorizontalHeaderLabels([c.label for c in self._schema])
        self.verticalHeader().setVisible(False)
        self.setWordWrap(True)
        self.setSortingEnabled(True)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionsMovable(True)
        header.setStretchLastSection(True)
        header.sectionResized.connect(self._on_section_resized)
        header.sectionMoved.connect(self._on_section_moved)
        header.sortIndicatorChanged.connect(self._on_sort_changed)

    def apply_preferences(self, table_prefs: Dict) -> None:
        self._restoring = True
        cols = sorted(table_prefs.get("columns", []), key=lambda x: int(x.get("order", 0)))
        for col in cols:
            idx = self._id_to_index.get(col.get("id"))
            if idx is None:
                continue
            self.setColumnHidden(idx, not bool(col.get("visible", True)))
            self.setColumnWidth(idx, int(col.get("width", 140)))

        for visual, col in enumerate(cols):
            idx = self._id_to_index.get(col.get("id"))
            if idx is None:
                continue
            logical_at_visual = self.horizontalHeader().logicalIndex(visual)
            if logical_at_visual != idx:
                self.horizontalHeader().moveSection(self.horizontalHeader().visualIndex(idx), visual)

        sort = table_prefs.get("sort", {})
        sort_idx = self._id_to_index.get(sort.get("id", ""))
        if sort_idx is not None:
            order = Qt.AscendingOrder if str(sort.get("direction", "asc")).lower() == "asc" else Qt.DescendingOrder
            self.sortItems(sort_idx, order)
            self.horizontalHeader().setSortIndicator(sort_idx, order)
        self._restoring = False

    def extract_preferences(self) -> Dict:
        columns = []
        header = self.horizontalHeader()
        for visual in range(self.columnCount()):
            logical = header.logicalIndex(visual)
            schema = self._schema[logical]
            columns.append(
                {
                    "id": schema.id,
                    "visible": not self.isColumnHidden(logical),
                    "order": visual,
                    "width": self.columnWidth(logical),
                }
            )
        sort_idx = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        return {
            "columns": columns,
            "sort": {
                "id": self._schema[sort_idx].id if 0 <= sort_idx < len(self._schema) else "id",
                "direction": "asc" if sort_order == Qt.AscendingOrder else "desc",
            },
        }

    def _emit_if_active(self) -> None:
        if self._restoring:
            return
        self.preferences_changed.emit(self.extract_preferences())

    def _on_section_resized(self, *_args) -> None:
        self._emit_if_active()

    def _on_section_moved(self, *_args) -> None:
        self._emit_if_active()

    def _on_sort_changed(self, *_args) -> None:
        self._emit_if_active()

    def set_rows(self, rows: List[Dict[str, str]]) -> None:
        self.setRowCount(0)
        for row_data in rows:
            row = self.rowCount()
            self.insertRow(row)
            for idx, col in enumerate(self._schema):
                value = str(row_data.get(col.id, ""))
                item = QTableWidgetItem(value)
                if col.id in self.LEFT_ALIGNED_COLUMN_IDS:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                if col.id == "prazo" and row_data.get("prazo_tooltip"):
                    item.setToolTip(str(row_data.get("prazo_tooltip")))
                self.setItem(row, idx, item)
        self.resizeRowsToContents()
