from __future__ import annotations

from typing import Tuple

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QAbstractItemView, QTableView

from mydemands.ui.stylesheets import BASE_QSS, DARK_COLORS_QSS, LIGHT_COLORS_QSS


def build_app_stylesheet(theme: str = "light") -> str:
    normalized = (theme or "light").strip().lower()
    colors = DARK_COLORS_QSS if normalized == "dark" else LIGHT_COLORS_QSS
    return BASE_QSS + "\n" + colors


def status_color(status: str) -> Tuple[int, int, int]:
    s = (status or "").strip().lower()
    if s == "concluído" or s == "concluido":
        return (210, 242, 220)
    if s == "não iniciada" or s == "nao iniciada" or s == "não iniciado" or s == "nao iniciado":
        return (255, 228, 230)
    if s == "requer revisão" or s == "requer revisao":
        return (237, 233, 254)
    if s == "em espera":
        return (255, 243, 205)
    if s == "cancelado":
        return (238, 238, 238)
    return (230, 239, 255)


def timing_color(timing: str) -> Tuple[int, int, int]:
    t = (timing or "").strip().lower()
    if "atras" in t:
        return (255, 228, 230)
    if "sem prazo" in t:
        return (243, 244, 246)
    if "dentro" in t or "no prazo" in t:
        return (220, 252, 231)
    if "conclu" in t:
        return (224, 231, 255)
    return (243, 244, 246)


def luminance(color: QColor) -> float:
    r = color.redF()
    g = color.greenF()
    b = color.blueF()
    return (0.299 * r) + (0.587 * g) + (0.114 * b)


def _relative_luminance(color: QColor) -> float:
    def _channel(c: float) -> float:
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * _channel(color.redF())
        + 0.7152 * _channel(color.greenF())
        + 0.0722 * _channel(color.blueF())
    )


def _contrast_ratio(color_a: QColor, color_b: QColor) -> float:
    lum_a = _relative_luminance(color_a)
    lum_b = _relative_luminance(color_b)
    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def best_text_color(bg_color: QColor) -> QColor:
    white = QColor("white")
    black = QColor("black")
    return white if _contrast_ratio(bg_color, white) >= _contrast_ratio(bg_color, black) else black


def _upsert_selection_rule(existing_qss: str, selection_qss: str) -> str:
    start_marker = "/* dynamic-table-selection:start */"
    end_marker = "/* dynamic-table-selection:end */"
    start_idx = existing_qss.find(start_marker)
    end_idx = existing_qss.find(end_marker)
    if start_idx >= 0 and end_idx > start_idx:
        end_idx += len(end_marker)
        return (existing_qss[:start_idx].rstrip() + "\n" + selection_qss).strip()
    if not existing_qss.strip():
        return selection_qss
    return existing_qss.rstrip() + "\n\n" + selection_qss


def apply_dynamic_selection_style(table: QTableView) -> None:
    palette = table.palette()
    bg_color = palette.color(QPalette.Base)
    theme_luminance = luminance(bg_color)
    is_light_theme = theme_luminance > 0.5

    selection_bg = QColor(58, 126, 246) if is_light_theme else QColor(84, 160, 255)
    selection_text = QColor("white") if is_light_theme else best_text_color(selection_bg)

    selection_qss = (
        "/* dynamic-table-selection:start */\n"
        "QTableView::item:selected {\n"
        f"    background-color: {selection_bg.name()};\n"
        f"    color: {selection_text.name()};\n"
        "}\n"
        "QTableWidget::item:selected {\n"
        f"    background-color: {selection_bg.name()};\n"
        f"    color: {selection_text.name()};\n"
        "}\n"
        "/* dynamic-table-selection:end */"
    )

    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setStyleSheet(_upsert_selection_rule(table.styleSheet(), selection_qss))
