from __future__ import annotations

from typing import Any, Callable, Dict, List

from PySide6.QtCore import QEvent, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QDrag, QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mydemands.dashboard.eisenhower_classifier import QUADRANTS, EisenhowerClassifierService
from mydemands.dashboard.eisenhower_dnd import EisenhowerDnDController


class EisenhowerThemeManager:
    @staticmethod
    def tokens(is_dark: bool) -> Dict[str, Dict[str, str]]:
        accent = {
            "q1": "#dc2626",
            "q2": "#eab308",
            "q3": "#16a34a",
            "q4": "#2563eb",
        }

        if is_dark:
            column_bg = "#111827"
            column_border = "#374151"
            column_header = "#f9fafb"
            count = "#f3f4f6"
            text_primary = "#f9fafb"
            text_secondary = "#e5e7eb"
            cards = {
                "q1": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(120,41,45,0.88), stop:1 rgba(90,33,36,0.9))",
                "q2": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(113,88,28,0.86), stop:1 rgba(86,68,23,0.9))",
                "q3": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(43,90,58,0.86), stop:1 rgba(35,70,47,0.9))",
                "q4": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(37,76,119,0.86), stop:1 rgba(30,58,95,0.9))",
            }
            card_border = "#4b5563"
            hover_overlay = "rgba(255,255,255,0.05)"
            dragover_background = "#1f2937"
            card_select_outline = "2px solid {accent}"
        else:
            column_bg = "#f3f4f6"
            column_border = "#d1d5db"
            column_header = "#111827"
            count = "#1f2937"
            text_primary = "#111827"
            text_secondary = "#4b5563"
            cards = {
                "q1": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(245,196,198,0.96), stop:1 rgba(240,183,186,0.96))",
                "q2": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(247,232,178,0.96), stop:1 rgba(242,223,158,0.96))",
                "q3": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(198,224,192,0.96), stop:1 rgba(184,213,176,0.96))",
                "q4": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(190,211,232,0.96), stop:1 rgba(176,201,225,0.96))",
            }
            card_border = "#dbe3f0"
            hover_overlay = "rgba(17,24,39,0.03)"
            dragover_background = "#eef2ff"
            card_select_outline = "2px solid {accent}"

        return {
            key: {
                "accent": value,
                "column_border": column_border,
                "column_background": column_bg,
                "column_header": column_header,
                "count_color": count,
                "text_primary": text_primary,
                "text_secondary": text_secondary,
                "card_background": cards[key],
                "card_border": card_border,
                "hover_overlay": hover_overlay,
                "dragover_background": dragover_background,
                "card_select_outline": card_select_outline,
            }
            for key, value in accent.items()
        }


class DemandCardWidget(QFrame):
    def __init__(
        self,
        row: Dict[str, Any],
        on_click: Callable[[Dict[str, Any], QWidget], None],
        on_double_click: Callable[[Dict[str, Any]], None],
        on_context_menu: Callable[[Dict[str, Any], QPoint], None],
    ):
        super().__init__()
        self._row = row
        self._on_click = on_click
        self._on_double_click = on_double_click
        self._on_context_menu = on_context_menu
        self.setObjectName("eisenhowerDemandCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(126)
        self.setFrameShape(QFrame.StyledPanel)
        self.setProperty("selected", False)
        self.setProperty("dragging", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        demand_number = str(row.get("ID") or row.get("_id") or "-")

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        id_label = QLabel(f"#{demand_number}")
        id_label.setObjectName("eisenhowerDemandId")
        header.addWidget(id_label)
        header.addStretch()

        priority = QLabel(f"Prioridade: {row.get('Prioridade') or 'Média'}")
        priority.setObjectName("eisenhowerPriority")
        header.addWidget(priority)

        desc_label = QLabel()
        desc_label.setObjectName("eisenhowerDescription")
        desc_label.setWordWrap(False)
        desc_label.setTextInteractionFlags(Qt.NoTextInteraction)
        desc_label.setToolTip((row.get("Descrição") or "Sem descrição").strip())

        deadline = (row.get("Prazo") or "Sem prazo").strip() or "Sem prazo"
        info = QLabel(f"Prazo: {deadline}")
        info.setObjectName("eisenhowerMetaInfo")
        info.setWordWrap(False)

        layout.addLayout(header)
        layout.addWidget(desc_label)
        layout.addStretch(1)
        layout.addWidget(info)

        self._desc_label = desc_label
        self._set_description()

    def _set_description(self) -> None:
        raw = (self._row.get("Descrição") or "Sem descrição").replace("\n", " ").strip()
        metrics = QFontMetrics(self._desc_label.font())
        width = max(self.width() - 36, 70)
        self._desc_label.setText(metrics.elidedText(raw, Qt.ElideRight, width))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._set_description()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self._on_click(self._row, self)
        if event.button() == Qt.RightButton:
            self._on_context_menu(self._row, event.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        if event.button() == Qt.LeftButton:
            self._on_double_click(self._row)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_dragging(self, dragging: bool) -> None:
        self.setProperty("dragging", dragging)
        self.style().unpolish(self)
        self.style().polish(self)


class QuadrantListWidget(QListWidget):
    def __init__(
        self,
        quadrant_key: str,
        on_card_click: Callable[[Dict[str, Any], QWidget], None],
        on_card_double_click: Callable[[Dict[str, Any]], None],
        on_card_context_menu: Callable[[Dict[str, Any], QPoint], None],
        on_move_request: Callable[[str, str, Dict[str, Any]], bool] | None = None,
    ):
        super().__init__()
        self.quadrant_key = quadrant_key
        self._on_card_click = on_card_click
        self._on_card_double_click = on_card_double_click
        self._on_card_context_menu = on_card_context_menu
        self._on_move_request = on_move_request

        self.setObjectName(f"{quadrant_key}_list")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.viewport().setAcceptDrops(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setAlternatingRowColors(False)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSpacing(8)
        self.setFrameShape(QFrame.NoFrame)

    def add_row(self, row: Dict[str, Any], target_index: int | None = None) -> None:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, row)
        item.setSizeHint(QSize(0, 136))
        if isinstance(target_index, int) and 0 <= target_index <= self.count():
            self.insertItem(target_index, item)
        else:
            self.addItem(item)
        self.setItemWidget(item, DemandCardWidget(row, self._on_card_click, self._on_card_double_click, self._on_card_context_menu))

    def _update_dragover(self, enabled: bool) -> None:
        self.setProperty("dragover", enabled)
        self.style().unpolish(self)
        self.style().polish(self)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        widget = self.itemWidget(item) if item else None
        if widget is not None:
            widget.set_dragging(True)
            pix = widget.grab()
            drag = QDrag(self)
            drag.setMimeData(self.mimeData(self.selectedItems()))
            drag.setPixmap(pix)
            drag.exec(Qt.MoveAction)
            widget.set_dragging(False)
            return
        super().startDrag(supportedActions)

    def dragEnterEvent(self, event):
        if isinstance(event.source(), QuadrantListWidget):
            event.acceptProposedAction()
            self._update_dragover(True)
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if isinstance(event.source(), QuadrantListWidget):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        super().dragLeaveEvent(event)
        self._update_dragover(False)

    def dropEvent(self, event):
        source = event.source()
        self._update_dragover(False)
        if not isinstance(source, QuadrantListWidget):
            event.ignore()
            return

        source_item = source.currentItem()
        row = source_item.data(Qt.UserRole) if source_item else None
        if not isinstance(row, dict):
            event.ignore()
            return

        target_index = self.indexAt(event.position().toPoint()).row()
        if target_index < 0:
            target_index = self.count()

        if source is self:
            super().dropEvent(event)
            return

        source_row_idx = source.row(source_item)
        source.takeItem(source_row_idx)
        self.add_row(row, target_index)
        self.setCurrentRow(target_index)

        moved_ok = bool(self._on_move_request and self._on_move_request(source.quadrant_key, self.quadrant_key, row))
        if moved_ok:
            event.acceptProposedAction()
            return

        rollback_item = self.takeItem(target_index)
        del rollback_item
        source.add_row(row, source_row_idx)
        source.setCurrentRow(source_row_idx)
        event.ignore()


class EisenhowerView(QWidget):
    context_action_requested = Signal(str, dict)

    def __init__(
        self,
        on_card_double_click,
        on_move_card: Callable[[str, str, Dict[str, Any]], bool] | None = None,
        classifier: EisenhowerClassifierService | None = None,
        user_id: str = "anonimo",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._on_card_double_click = on_card_double_click
        self._classifier = classifier or EisenhowerClassifierService()
        self._user_id = user_id or "anonimo"
        self._dnd_controller = EisenhowerDnDController(on_move_card) if on_move_card else None
        self.last_groups: Dict[str, List[Dict[str, Any]]] = {q.key: [] for q in QUADRANTS}
        self._columns_lists: Dict[str, QuadrantListWidget] = {}
        self._selected_card_widget: DemandCardWidget | None = None
        self._is_dark = False

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        for quadrant in QUADRANTS:
            column = QFrame()
            column.setObjectName(f"eisenhowerColumn_{quadrant.key}")
            column.setFrameShape(QFrame.StyledPanel)

            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(12, 10, 12, 12)
            column_layout.setSpacing(10)

            accent_line = QFrame()
            accent_line.setObjectName(f"{quadrant.key}_accent")
            accent_line.setFixedHeight(4)

            title = QLabel(quadrant.title)
            title.setObjectName("eisenhowerQuadrantTitle")
            count = QLabel("0")
            count.setObjectName(f"{quadrant.key}_count")

            header = QVBoxLayout()
            header.setSpacing(2)
            header.addWidget(title, alignment=Qt.AlignHCenter)
            header.addWidget(count, alignment=Qt.AlignHCenter)

            list_widget = QuadrantListWidget(
                quadrant.key,
                self._select_card,
                self._on_card_double_click,
                self._show_context_menu,
                self._handle_move_request,
            )
            list_widget.viewport().installEventFilter(self)

            column_layout.addLayout(header)
            column_layout.addWidget(accent_line)
            column_layout.addWidget(list_widget, 1)
            root.addWidget(column, 1)

            self._columns_lists[quadrant.key] = list_widget

        self.apply_theme("light")

    def _column_stylesheet(self, key: str, t: Dict[str, str]) -> str:
        return (
            f"QFrame#eisenhowerColumn_{key} {{"
            f"background: {t['column_background']};"
            f"border: 1px solid {t['column_border']};"
            f"border-radius: 14px;"
            f"}}"
            f"QFrame#{key}_accent {{background: {t['accent']}; border: none; border-top-left-radius: 4px; border-top-right-radius: 4px;}}"
            f"QLabel#eisenhowerQuadrantTitle {{color: {t['column_header']}; font-size: 15px; font-weight: 600;}}"
            f"QLabel#{key}_count {{color: {t['count_color']}; font-size: 14px; font-weight: 600;}}"
        )

    def _list_stylesheet(self, key: str, t: Dict[str, str]) -> str:
        return (
            f"QListWidget#{key}_list {{"
            f"background: transparent; border: none; padding: 2px; outline: 0;"
            f"}}"
            f"QListWidget#{key}_list[dragover='true'] {{"
            f"border: 2px dashed {t['accent']}; border-radius: 12px; background: {t['dragover_background']};"
            f"}}"
            f"QFrame#eisenhowerDemandCard {{"
            f"border: 1px solid {t['card_border']}; border-radius: 14px; background: {t['card_background']};"
            f"}}"
            f"QFrame#eisenhowerDemandCard:hover {{border-color: {t['accent']};}}"
            f"QFrame#eisenhowerDemandCard[selected='true'] {{border: {t['card_select_outline'].format(accent=t['accent'])};}}"
            f"QFrame#eisenhowerDemandCard[dragging='true'] {{border: 2px dashed {t['accent']};}}"
            f"QLabel#eisenhowerDemandId {{font-size: 14px; font-weight: 700; color: {t['text_primary']};}}"
            f"QLabel#eisenhowerPriority {{font-size: 12px; color: {t['text_secondary']};}}"
            f"QLabel#eisenhowerDescription {{font-size: 14px; font-weight: 600; color: {t['text_primary']};}}"
            f"QLabel#eisenhowerMetaInfo {{font-size: 12px; color: {t['text_secondary']};}}"
        )

    def apply_theme(self, theme_name: str) -> None:
        self._is_dark = (theme_name or "light").strip().lower() == "dark"
        color_tokens = EisenhowerThemeManager.tokens(self._is_dark)

        for quadrant in QUADRANTS:
            token = color_tokens[quadrant.key]
            column = self.findChild(QFrame, f"eisenhowerColumn_{quadrant.key}")
            if column is not None:
                column.setProperty("accent", token["accent"])
                column.setProperty("columnBorder", token["column_border"])
                column.setStyleSheet(self._column_stylesheet(quadrant.key, token))

            list_widget = self._columns_lists.get(quadrant.key)
            if list_widget is not None:
                list_widget.setStyleSheet(self._list_stylesheet(quadrant.key, token))

    def _handle_move_request(self, source_quadrant: str, target_quadrant: str, row: Dict[str, Any]) -> bool:
        if not self._dnd_controller:
            return False
        return self._dnd_controller.handle_move(source_quadrant, target_quadrant, row)

    def _select_card(self, row: Dict[str, Any], card: QWidget) -> None:
        if isinstance(self._selected_card_widget, DemandCardWidget) and self._selected_card_widget is not card:
            self._selected_card_widget.set_selected(False)
        if isinstance(card, DemandCardWidget):
            card.set_selected(True)
            self._selected_card_widget = card

    def clear_selection(self) -> None:
        if isinstance(self._selected_card_widget, DemandCardWidget):
            self._selected_card_widget.set_selected(False)
        self._selected_card_widget = None

    def _show_context_menu(self, row: Dict[str, Any], global_pos: QPoint) -> None:
        self.context_action_requested.emit("open", row | {"_context_pos": global_pos})

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonPress and hasattr(watched, "parent"):
            list_widget = watched.parent()
            if isinstance(list_widget, QListWidget) and list_widget.itemAt(event.pos()) is None:
                self.clear_selection()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.clear_selection()

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.clear_selection()
        self.last_groups = self._classifier.group_rows(rows, user_id=self._user_id)
        for quadrant in QUADRANTS:
            key = quadrant.key
            rows_in_group = self.last_groups.get(key, [])
            list_widget = self._columns_lists[key]
            list_widget.clear()
            for row in rows_in_group:
                list_widget.add_row(row)
            count_label = self.findChild(QLabel, f"{key}_count")
            if count_label is not None:
                count_label.setText(str(len(rows_in_group)))
