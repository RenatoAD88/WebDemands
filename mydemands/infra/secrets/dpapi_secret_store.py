from __future__ import annotations

import base64
import json
from pathlib import Path

from mydemands.infra.secrets.secret_store import ISecretStore

try:
    import win32crypt  # type: ignore
except Exception:  # pragma: no cover - platform fallback
    win32crypt = None


class WindowsDpapiSecretStore(ISecretStore):
    def __init__(self, storage_file: Path, entropy: bytes | None = None):
        self.storage_file = storage_file
        self.entropy = entropy

    def _load(self) -> dict:
        if not self.storage_file.exists():
            return {}
        return json.loads(self.storage_file.read_text(encoding="utf-8"))

    def _save(self, payload: dict) -> None:
        self.storage_file.write_text(json.dumps(payload), encoding="utf-8")

    def _protect(self, value: bytes) -> bytes:
        if win32crypt is None:
            return value
        return win32crypt.CryptProtectData(value, "MyDemands", self.entropy, None, None, 0)

    def _unprotect(self, value: bytes) -> bytes:
        if win32crypt is None:
            return value
        return win32crypt.CryptUnprotectData(value, None, self.entropy, None, 0)[1]

    def set(self, key: str, value: bytes) -> None:
        payload = self._load()
        protected = self._protect(value)
        payload[key] = base64.b64encode(protected).decode("ascii")
        self._save(payload)

    def get(self, key: str) -> bytes | None:
        payload = self._load()
        encoded = payload.get(key)
        if not encoded:
            return None
        try:
            raw = base64.b64decode(encoded)
            return self._unprotect(raw)
        except Exception:
            payload.pop(key, None)
            self._save(payload)
            return None

    def delete(self, key: str) -> None:
        payload = self._load()
        if key in payload:
            del payload[key]
            self._save(payload)
