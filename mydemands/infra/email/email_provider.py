from __future__ import annotations

from abc import ABC, abstractmethod


class IEmailProvider(ABC):
    @abstractmethod
    def send(self, *, to_email: str, from_email: str, subject: str, body: str, reply_to: str | None = None) -> None:
        raise NotImplementedError
