from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from typing import Any, Callable, Dict, List

from csv_store import parse_prazos_list

PENDING_ACTIVE_STATUSES = {"não iniciada", "em andamento", "bloqueado", "requer revisão", "requer revisao"}
EISENHOWER_COLUMN_FIELD = "eisenhower_column"


@dataclass(frozen=True)
class EisenhowerQuadrant:
    key: str
    title: str


QUADRANTS: List[EisenhowerQuadrant] = [
    EisenhowerQuadrant("q1", "Importante e Urgente"),
    EisenhowerQuadrant("q2", "Não importante e Urgente"),
    EisenhowerQuadrant("q3", "Importante e Não urgente"),
    EisenhowerQuadrant("q4", "Não importante e Não urgente"),
]


class EisenhowerClassifierService:
    def __init__(self, today_provider: Callable[[], date] | None = None):
        self._today_provider = today_provider or date.today

    def should_include(self, row: Dict[str, Any]) -> bool:
        status = (row.get("Status") or "").strip().casefold()
        return status in PENDING_ACTIVE_STATUSES

    def classify(self, row: Dict[str, Any], user_id: str | None = None) -> str:
        if not self.should_include(row):
            return "excluded"

        persisted = self.persisted_column_for_user(row, user_id)
        if persisted:
            return persisted

        important = self._is_important(row)
        urgent = self._is_urgent(row)
        if important and urgent:
            return "q1"
        if (not important) and urgent:
            return "q2"
        if important and (not urgent):
            return "q3"
        return "q4"

    def group_rows(self, rows: List[Dict[str, Any]], user_id: str | None = None) -> Dict[str, List[Dict[str, Any]]]:
        groups = {q.key: [] for q in QUADRANTS}
        for row in rows:
            key = self.classify(row, user_id=user_id)
            if key in groups:
                groups[key].append(row)
        return groups

    def classify_initial(self, row: Dict[str, Any]) -> str:
        if not self.should_include(row):
            return "excluded"
        important = self._is_important(row)
        urgent = self._is_urgent(row)
        if important and urgent:
            return "q1"
        if (not important) and urgent:
            return "q2"
        if important and (not urgent):
            return "q3"
        return "q4"

    def persisted_column_for_user(self, row: Dict[str, Any], user_id: str | None) -> str:
        if not user_id:
            return ""
        mapping = parse_eisenhower_column_map(row.get(EISENHOWER_COLUMN_FIELD))
        value = str(mapping.get(user_id) or "").strip().lower()
        return value if value in {"q1", "q2", "q3", "q4"} else ""

    def _is_important(self, row: Dict[str, Any]) -> bool:
        priority = (row.get("Prioridade") or "Média").strip().casefold()
        if priority not in {"alta", "média", "media", "baixa"}:
            priority = "média"
        return priority in {"alta", "média", "media"}

    def _is_urgent(self, row: Dict[str, Any]) -> bool:
        is_urgent = (row.get("É Urgente?") or "Não").strip().casefold() == "sim"
        timing = (row.get("Timing") or "").strip().casefold()
        delayed = "atras" in timing
        return is_urgent or delayed or self._is_due_today(row)

    def _is_due_today(self, row: Dict[str, Any]) -> bool:
        today = self._today_provider()
        raw_deadline = str(row.get("Prazo") or "")
        normalized = raw_deadline.replace("*", "").replace("\n", ",")
        return today in parse_prazos_list(normalized)


def parse_eisenhower_column_map(raw_value: Any) -> Dict[str, str]:
    if isinstance(raw_value, dict):
        raw_map = raw_value
    else:
        raw = str(raw_value or "").strip()
        if not raw:
            return {}
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(loaded, dict):
            return {}
        raw_map = loaded

    parsed: Dict[str, str] = {}
    for user, column in raw_map.items():
        user_key = str(user or "").strip()
        column_value = str(column or "").strip().lower()
        if not user_key or column_value not in {"q1", "q2", "q3", "q4"}:
            continue
        parsed[user_key] = column_value
    return parsed


def dump_eisenhower_column_map(value: Dict[str, str]) -> str:
    normalized = parse_eisenhower_column_map(value)
    if not normalized:
        return ""
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)
