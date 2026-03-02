from __future__ import annotations

from typing import Any, Callable, Dict

from mydemands.dashboard.eisenhower_classifier import EISENHOWER_COLUMN_FIELD


class EisenhowerDnDController:

    def __init__(self, move_executor: Callable[[Dict[str, Any], Dict[str, str]], None] | None):
        self._move_executor = move_executor

    def build_payload_for_target(self, target_quadrant: str, row: Dict[str, Any] | None = None) -> Dict[str, str]:
        if target_quadrant not in {"q1", "q2", "q3", "q4"}:
            return {}
        return {EISENHOWER_COLUMN_FIELD: target_quadrant}

    def handle_move(self, source_quadrant: str, target_quadrant: str, row: Dict[str, Any]) -> bool:
        if source_quadrant == target_quadrant or not self._move_executor:
            return False
        payload = self.build_payload_for_target(target_quadrant, row)
        if not payload:
            return False
        self._move_executor(row, payload)
        return True
