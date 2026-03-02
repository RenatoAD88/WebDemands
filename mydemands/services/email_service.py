from __future__ import annotations

from mydemands.domain.models import EmailSettings
from mydemands.infra.email.email_provider import IEmailProvider
from mydemands.infra.email.smtp_provider import SmtpEmailProvider
from mydemands.infra.repositories.settings_repository import SettingsRepository
from mydemands.infra.secrets.secret_store import ISecretStore

SMTP_PASSWORD_KEY = "smtp_app_password"
LEGACY_SMTP_PASSWORD_KEY = "smtp_password"
DEFAULT_RECOVERY_SUBJECT = "MyDemands - Recuperação de senha"
PROVISIONAL_MINUTES = 15
TEST_PROVISIONAL_PASSWORD = "Prov_1234567890"

DEFAULT_RECOVERY_BODY = (
    "Olá!\n\n"
    "Aqui está sua senha provisória para acesso.\n"
    "Se não encontrar este e-mail, verifique também a caixa de spam.\n\n"
    "Senha provisória: {PASSWORD}\n\n"
    "Esta senha expira em {MINUTOS} minutos.\n"
    "Ao entrar na aplicação, você deverá definir sua senha final."
)


class EmailService:
    def __init__(
        self,
        settings_repository: SettingsRepository,
        secret_store: ISecretStore,
        provider: IEmailProvider | None = None,
    ):
        self.settings_repository = settings_repository
        self.secret_store = secret_store
        self._provider = provider

    def load_settings(self) -> EmailSettings | None:
        return self.settings_repository.load_email_settings()

    def save_smtp_password(self, smtp_password: str) -> None:
        self.secret_store.set(SMTP_PASSWORD_KEY, smtp_password.encode("utf-8"))

    def get_smtp_password(self) -> str | None:
        secret = self.secret_store.get(SMTP_PASSWORD_KEY)
        if not secret:
            legacy = self.secret_store.get(LEGACY_SMTP_PASSWORD_KEY)
            if legacy:
                self.secret_store.set(SMTP_PASSWORD_KEY, legacy)
                secret = legacy
        if not secret:
            return None
        return secret.decode("utf-8")

    def get_smtp_password_for_send(self) -> str:
        password = self.get_smtp_password()
        if not password:
            raise RuntimeError("SMTP App Password não configurada")
        return password

    def save_smtp_settings(self, settings: EmailSettings, smtp_password: str | None = None) -> None:
        self.settings_repository.save_email_settings(settings)
        if smtp_password and smtp_password.strip():
            self.save_smtp_password(smtp_password.strip())

    @staticmethod
    def migrate_legacy_recovery_template(body_template: str) -> str:
        migrated = body_template or ""
        if not migrated.strip():
            return DEFAULT_RECOVERY_BODY
        if "{TOKEN}" in migrated and "{PASSWORD}" not in migrated:
            migrated = migrated.replace("{TOKEN}", "{PASSWORD}")
            migrated = migrated.replace("Código provisório", "Senha provisória")
            migrated = migrated.replace("código provisório", "senha provisória")
        if "{MINUTOS}" not in migrated:
            migrated = f"{migrated.rstrip()}\n\nEsta senha expira em {{MINUTOS}} minutos."
        return migrated

    @staticmethod
    def validate_recovery_template(body_template: str) -> None:
        if "{TOKEN}" in body_template:
            raise ValueError("TOKEN_LEGACY_PLACEHOLDER")
        if "{PASSWORD}" not in body_template:
            raise ValueError("Body deve conter {PASSWORD}")
        if "{MINUTOS}" not in body_template:
            raise ValueError("Body deve conter {MINUTOS}")
        if "spam" not in body_template.lower():
            raise ValueError("Body deve orientar verificação de spam")

    @staticmethod
    def render_recovery_body(body_template: str, provisional_password: str) -> str:
        rendered = body_template.replace("{PASSWORD}", provisional_password).replace("{MINUTOS}", str(PROVISIONAL_MINUTES))
        if "{PASSWORD}" in rendered or "{MINUTOS}" in rendered:
            raise ValueError("Template de recuperação inválido")
        return rendered

    def get_provider(self, settings: EmailSettings | None = None, smtp_password: str | None = None) -> IEmailProvider:
        if self._provider:
            return self._provider
        effective_settings = settings or self.settings_repository.load_email_settings()
        if not effective_settings:
            raise RuntimeError("SMTP_NOT_CONFIGURED")
        password = smtp_password or self.get_smtp_password_for_send()
        return SmtpEmailProvider(
            host=effective_settings.smtp_host,
            port=effective_settings.smtp_port,
            username=effective_settings.smtp_username,
            password=password,
            use_tls=effective_settings.use_tls,
        )

    def send_recovery_email(self, to_email: str, provisional_password: str) -> None:
        settings = self.settings_repository.load_email_settings()
        if not settings:
            raise RuntimeError("SMTP_NOT_CONFIGURED")
        self.validate_recovery_template(settings.body_template)
        body = self.render_recovery_body(settings.body_template, provisional_password)
        subject = settings.subject_template or DEFAULT_RECOVERY_SUBJECT
        self.get_provider().send(
            to_email=to_email,
            from_email=settings.from_email,
            subject=subject,
            body=body,
            reply_to=settings.reply_to,
        )

    def send_test_email(
        self,
        to_email: str,
        settings_override: EmailSettings | None = None,
        smtp_password_override: str | None = None,
    ) -> None:
        settings = settings_override or self.settings_repository.load_email_settings()
        if not settings:
            raise RuntimeError("SMTP_NOT_CONFIGURED")
        self.validate_recovery_template(settings.body_template)
        body = self.render_recovery_body(settings.body_template, TEST_PROVISIONAL_PASSWORD)
        subject = settings.subject_template or DEFAULT_RECOVERY_SUBJECT
        smtp_password = smtp_password_override or self.get_smtp_password_for_send()
        self.get_provider(settings=settings, smtp_password=smtp_password).send(
            to_email=to_email,
            from_email=settings.from_email,
            subject=subject,
            body=body,
            reply_to=settings.reply_to,
        )
