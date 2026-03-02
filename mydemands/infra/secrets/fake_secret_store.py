from __future__ import annotations

from mydemands.infra.secrets.secret_store import ISecretStore


class FakeSecretStore(ISecretStore):
    def __init__(self):
        self._data: dict[str, bytes] = {}

    def set(self, key: str, value: bytes) -> None:
        self._data[key] = value

    def get(self, key: str) -> bytes | None:
        return self._data.get(key)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
