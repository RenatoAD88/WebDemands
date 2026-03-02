from __future__ import annotations

from typing import Any, Callable, Dict, Optional


PANEL_CLASS = None


class AIFieldBinding:
    def __init__(
        self,
        target_widget: Any,
        context_provider: Callable[[], Dict[str, Any]],
        generate_handler,
        on_apply: Optional[Callable[[str], None]] = None,
        field_name: str = "",
        demand_id: str = "",
    ):
        self.text_widget = target_widget
        self.context_provider = context_provider
        self.generate_handler = generate_handler
        self.on_apply = on_apply
        self.field_name = field_name
        self.demand_id = str(demand_id or "")
        self._last_original = ""

    def open_panel(self, parent=None):
        source = get_text(self.text_widget)

        global PANEL_CLASS
        if PANEL_CLASS is None:
            from ai_writing.ui_panel import AIWritingPanel
            PANEL_CLASS = AIWritingPanel

        context = dict(self.context_provider() or {})
        if self.field_name and not context.get("field"):
            context["field"] = self.field_name
        if self.demand_id and not context.get("demand_id"):
            context["demand_id"] = self.demand_id

        self._last_original = source

        def _apply_from_panel(suggestion: str) -> bool:
            if callable(self.on_apply):
                self.on_apply(suggestion)
            else:
                set_text(self.text_widget, suggestion)
                focus_widget_end(self.text_widget)
            return True

        panel = PANEL_CLASS(source, self.generate_handler, context, parent=parent, on_apply=_apply_from_panel)
        panel.exec()

    def undo_last(self):
        if self._last_original:
            set_text(self.text_widget, self._last_original)
            focus_widget_end(self.text_widget)


def attach_ai_writing(
    text_widget: Any,
    context_provider: Callable[[], Dict[str, Any]],
    generate_handler,
    on_apply: Optional[Callable[[str], None]] = None,
    field_name: str = "",
    demand_id: str = "",
):
    from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

    binding = AIFieldBinding(
        text_widget,
        context_provider,
        generate_handler,
        on_apply=on_apply,
        field_name=field_name,
        demand_id=demand_id,
    )
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(text_widget)

    btn = QPushButton("✨ Redigir com IA")
    btn.clicked.connect(lambda: binding.open_panel(parent=text_widget.window()))
    layout.addWidget(btn)

    text_widget._ai_binding = binding  # type: ignore[attr-defined]
    text_widget._ai_button = btn  # type: ignore[attr-defined]
    return wrapper


def set_text(text_widget: Any, suggestion: str) -> None:
    if hasattr(text_widget, "setPlainText"):
        text_widget.setPlainText(suggestion)
        return
    if hasattr(text_widget, "setText"):
        text_widget.setText(suggestion)
        return
    raise TypeError(f"Widget {type(text_widget).__name__} não suportado para aplicação de IA")


def get_text(text_widget: Any) -> str:
    if hasattr(text_widget, "toPlainText"):
        return text_widget.toPlainText()
    if hasattr(text_widget, "text"):
        return text_widget.text()
    return ""


def focus_widget_end(text_widget: Any) -> None:
    if hasattr(text_widget, "setFocus"):
        text_widget.setFocus()
    if hasattr(text_widget, "setCursorPosition") and hasattr(text_widget, "text"):
        text_widget.setCursorPosition(len(text_widget.text()))
        return
    if hasattr(text_widget, "moveCursor"):
        cursor = text_widget.textCursor() if hasattr(text_widget, "textCursor") else None
        move_op = getattr(getattr(cursor, "MoveOperation", None), "End", None) if cursor is not None else None
        if move_op is not None:
            text_widget.moveCursor(move_op)
            return
    if hasattr(text_widget, "textCursor") and hasattr(text_widget, "setTextCursor"):
        cursor = text_widget.textCursor()
        move_op = getattr(getattr(cursor, "MoveOperation", None), "End", None)
        if move_op is not None and hasattr(cursor, "movePosition"):
            cursor.movePosition(move_op)
        text_widget.setTextCursor(cursor)


# Backward-compatible aliases
apply_suggestion_to_widget = set_text
get_widget_text = get_text
