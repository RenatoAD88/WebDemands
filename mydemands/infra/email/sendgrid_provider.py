from __future__ import annotations

from mydemands.infra.email.email_provider import IEmailProvider


class SendGridEmailProvider(IEmailProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def send(self, *, to_email: str, from_email: str, subject: str, body: str, reply_to: str | None = None) -> None:
        raise NotImplementedError("SendGrid provider ainda não implementado")
