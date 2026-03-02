from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, List

from mydemands.dashboard.demandas_schema_registry import DemandasSchemaRegistry


class UserPreferencesStore:
    def load(self, user_id: str) -> Dict:
        raise NotImplementedError

    def save(self, user_id: str, payload: Dict) -> None:
        raise NotImplementedError


class LocalJsonPreferencesStore(UserPreferencesStore):
    def __init__(self, base_dir: Path | str | None = None) -> None:
        if base_dir is None:
            app_data = Path(os.getenv("APPDATA") or Path.home())
            self.base_dir = app_data / "MyDemands"
        else:
            self.base_dir = Path(base_dir)

    def _file(self, user_id: str) -> Path:
        root = self.base_dir / "users" / user_id
        root.mkdir(parents=True, exist_ok=True)
        return root / "preferences.json"

    def load(self, user_id: str) -> Dict:
        fp = self._file(user_id)
        if not fp.exists():
            return {"schema_version": 0, "tables": {}}
        return json.loads(fp.read_text(encoding="utf-8"))

    def save(self, user_id: str, payload: Dict) -> None:
        fp = self._file(user_id)
        tmp = fp.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(fp)


class PreferencesMigrationService:
    def migrate(self, payload: Dict, registry: DemandasSchemaRegistry) -> Dict:
        migrated = deepcopy(payload or {"schema_version": 0, "tables": {}})
        tables = migrated.setdefault("tables", {})
        by_id = registry.by_id()
        for table_key, table in list(tables.items()):
            columns = [c for c in table.get("columns", []) if c.get("id") in by_id]
            existing_ids = {c.get("id") for c in columns}
            next_order = len(columns)
            for schema_col in registry.demand_columns():
                if schema_col.id not in existing_ids:
                    columns.append({"id": schema_col.id, "visible": False, "order": next_order, "width": schema_col.default_width})
                    next_order += 1
            table["columns"] = columns
            tables[table_key] = table
        migrated["schema_version"] = registry.SCHEMA_VERSION
        return migrated


class PreferencesNormalizer:
    def normalize(self, table_prefs: Dict, registry: DemandasSchemaRegistry) -> Dict:
        normalized = deepcopy(table_prefs)
        cols = normalized.get("columns", [])
        valid_ids = {c.id for c in registry.demand_columns()}
        cols = [c for c in cols if c.get("id") in valid_ids]
        seen = set()
        deduped = []
        for c in sorted(cols, key=lambda x: int(x.get("order", 0))):
            cid = c.get("id")
            if cid in seen:
                continue
            seen.add(cid)
            c["width"] = max(60, min(int(c.get("width", 140)), 800))
            deduped.append(c)

        if not any(bool(c.get("visible")) for c in deduped):
            fallback = next((c for c in deduped if c.get("id") == "id"), None)
            if fallback is None and registry.demand_columns():
                fallback = {"id": registry.demand_columns()[0].id, "visible": True, "order": 0, "width": 90}
                deduped.insert(0, fallback)
            if fallback is not None:
                fallback["visible"] = True

        for idx, col in enumerate(deduped):
            col["order"] = idx

        normalized["columns"] = deduped
        return normalized


class GridPreferencesService:
    def __init__(
        self,
        store: UserPreferencesStore,
        registry: DemandasSchemaRegistry | None = None,
        migration_service: PreferencesMigrationService | None = None,
        normalizer: PreferencesNormalizer | None = None,
    ) -> None:
        self.store = store
        self.registry = registry or DemandasSchemaRegistry()
        self.migration_service = migration_service or PreferencesMigrationService()
        self.normalizer = normalizer or PreferencesNormalizer()

    def load_table_preferences(self, user_id: str, table_key: str, default_visible_ids: List[str] | None = None) -> Dict:
        payload = self.migration_service.migrate(self.store.load(user_id), self.registry)
        table = payload.setdefault("tables", {}).get(table_key)
        if not table:
            table = self.registry.default_table_preferences(default_visible_ids)
            payload["tables"][table_key] = table
            self.store.save(user_id, payload)
        normalized = self.normalizer.normalize(table, self.registry)
        payload["tables"][table_key] = normalized
        self.store.save(user_id, payload)
        return normalized

    def save_table_preferences(self, user_id: str, table_key: str, table_prefs: Dict) -> Dict:
        payload = self.migration_service.migrate(self.store.load(user_id), self.registry)
        payload.setdefault("tables", {})[table_key] = self.normalizer.normalize(table_prefs, self.registry)
        self.store.save(user_id, payload)
        return payload["tables"][table_key]

    def reset_table_preferences(self, user_id: str, table_key: str, default_visible_ids: List[str] | None = None) -> Dict:
        payload = self.migration_service.migrate(self.store.load(user_id), self.registry)
        payload.setdefault("tables", {})[table_key] = self.registry.default_table_preferences(default_visible_ids)
        payload["tables"][table_key] = self.normalizer.normalize(payload["tables"][table_key], self.registry)
        self.store.save(user_id, payload)
        return payload["tables"][table_key]
