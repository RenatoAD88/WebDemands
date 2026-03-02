from __future__ import annotations

from abc import ABC, abstractmethod


class ISecretStore(ABC):
    @abstractmethod
    def set(self, key: str, value: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError
