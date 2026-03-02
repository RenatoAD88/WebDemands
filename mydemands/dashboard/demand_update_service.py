from __future__ import annotations

from typing import Any, Callable, Dict


class DemandUpdateService:
    def __init__(self, update_callable: Callable[[str, Dict[str, Any]], None], after_update: Callable[[], None] | None = None):
        self._update_callable = update_callable
        self._after_update = after_update

    def update(self, demand_id: str, changes: Dict[str, Any]) -> None:
        self._update_callable(demand_id, changes)
        if self._after_update:
            self._after_update()
