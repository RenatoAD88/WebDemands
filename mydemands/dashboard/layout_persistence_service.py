from __future__ import annotations

import json
import os
from typing import List


DEFAULT_ORDER = ["big_numbers", "progresso", "graficos", "alertas"]


class LayoutPersistenceService:
    def __init__(self, base_dir: str, file_name: str = "monitoramento_layouts.json") -> None:
        self.base_dir = base_dir
        self.file_path = os.path.join(base_dir, file_name)

    def load(self, user_email: str) -> List[str]:
        payload = self._read()
        order = payload.get(user_email)
        if not isinstance(order, list):
            return DEFAULT_ORDER.copy()
        sanitized = [str(item) for item in order if str(item) in DEFAULT_ORDER]
        for block in DEFAULT_ORDER:
            if block not in sanitized:
                sanitized.append(block)
        return sanitized

    def save(self, user_email: str, order: List[str]) -> None:
        payload = self._read()
        sanitized = [block for block in order if block in DEFAULT_ORDER]
        for block in DEFAULT_ORDER:
            if block not in sanitized:
                sanitized.append(block)
        payload[user_email] = sanitized
        os.makedirs(self.base_dir, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _read(self) -> dict:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
