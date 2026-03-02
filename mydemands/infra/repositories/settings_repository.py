from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from mydemands.domain.models import EmailSettings


class SettingsRepository:
    def __init__(self, settings_file: Path):
        self.settings_file = settings_file

    def load_email_settings(self) -> Optional[EmailSettings]:
        if not self.settings_file.exists():
            return None
        payload = json.loads(self.settings_file.read_text(encoding="utf-8"))
        return EmailSettings(**payload)

    def save_email_settings(self, settings: EmailSettings) -> None:
        self.settings_file.write_text(
            json.dumps(
                {
                    "smtp_host": settings.smtp_host,
                    "smtp_port": settings.smtp_port,
                    "use_tls": settings.use_tls,
                    "smtp_username": settings.smtp_username,
                    "from_email": settings.from_email,
                    "reply_to": settings.reply_to,
                    "subject_template": settings.subject_template,
                    "body_template": settings.body_template,
                }
            ),
            encoding="utf-8",
        )
