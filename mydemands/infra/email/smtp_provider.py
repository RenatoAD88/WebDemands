from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from mydemands.infra.email.email_provider import IEmailProvider


class SmtpEmailProvider(IEmailProvider):
    def __init__(self, host: str, port: int, username: str, password: str, use_tls: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send(self, *, to_email: str, from_email: str, subject: str, body: str, reply_to: str | None = None) -> None:
        message = MIMEText(body, _charset="utf-8")
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        if reply_to:
            message["Reply-To"] = reply_to

        with smtplib.SMTP(self.host, self.port) as smtp:
            smtp.ehlo()
            if self.use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(self.username, self.password)
            smtp.sendmail(from_email, [to_email], message.as_string())
