from __future__ import annotations

import json
import os
from typing import Dict, Any

PREFS_FILE = "ui_prefs.json"


def prefs_path(base_dir: str) -> str:
    return os.path.join(base_dir, PREFS_FILE)


def load_prefs(base_dir: str) -> Dict[str, Any]:
    path = prefs_path(base_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_prefs(base_dir: str, data: Dict[str, Any]) -> None:
    path = prefs_path(base_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data or {}, f, ensure_ascii=False, indent=2)
