from mydemands.domain.models import EmailSettings
from mydemands.services.email_service import EmailService


def test_email_service_renders_password_and_minutes():
    template = "Senha: {PASSWORD}. Expira em {MINUTOS} minutos."

    rendered = EmailService.render_recovery_body(template, "Prov_abc")

    assert "Prov_abc" in rendered
    assert "15" in rendered
    assert "{PASSWORD}" not in rendered
    assert "{MINUTOS}" not in rendered


def test_test_send_uses_rendered_template(env):
    email_service: EmailService = env["email"]
    settings = EmailSettings(
        smtp_host="smtp.test",
        smtp_port=587,
        use_tls=True,
        smtp_username="user",
        from_email="noreply@test.com",
        reply_to=None,
        subject_template="Recuperação",
        body_template="Senha provisória: {PASSWORD}. Expira em {MINUTOS} minutos. Verifique spam.",
    )
    email_service.save_smtp_settings(settings, smtp_password="secret")

    email_service.send_test_email("master@test.com")

    payload = env["provider"].calls[0]
    assert "{PASSWORD}" not in payload["body"]
    assert "{MINUTOS}" not in payload["body"]
    assert "Prov_1234567890" in payload["body"]
