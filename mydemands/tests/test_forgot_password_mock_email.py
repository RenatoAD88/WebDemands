import re
from datetime import datetime, timedelta

from mydemands.domain.models import EmailSettings
from mydemands.services.auth_service import verify_password
from mydemands.services.email_service import SMTP_PASSWORD_KEY


def _configure(env):
    env["settings"].save_email_settings(
        EmailSettings(
            smtp_host="smtp.test",
            smtp_port=587,
            use_tls=True,
            smtp_username="user",
            from_email="noreply@test.com",
            reply_to=None,
            subject_template="Recuperação",
            body_template="Senha provisória: {PASSWORD}. Expira em {MINUTOS} minutos. Verifique spam.",
        )
    )
    env["secrets"].set(SMTP_PASSWORD_KEY, b"secret")


def test_request_reset_sets_provisional_and_sends_email(env, monkeypatch):
    env["auth"].register("user@test.com", "Abcdef1!")
    old_hash = env["users"].get_by_email("user@test.com").password_hash
    _configure(env)

    captured = {}

    def fake_generate():
        pwd = "Prov_1234567890"
        captured["password"] = pwd
        return pwd

    monkeypatch.setattr(env["reset"], "_generate_provisional_password", fake_generate)

    message = env["reset"].request_password_reset("user@test.com")

    user = env["users"].get_by_email("user@test.com")
    assert user is not None
    assert re.match(r"^Prov_\d{10}$", captured["password"])
    assert user.password_hash != old_hash
    assert verify_password(captured["password"], user.password_hash)
    assert user.must_change_password is True
    assert user.provisional_expires_at is not None
    expires_at = datetime.fromisoformat(user.provisional_expires_at)
    remaining = expires_at - datetime.utcnow()
    assert timedelta(minutes=14, seconds=30) <= remaining <= timedelta(minutes=15, seconds=5)

    calls = env["provider"].calls
    assert len(calls) == 1
    payload = calls[0]
    assert captured["password"] in payload["body"]
    assert "spam" in payload["body"].lower()
    assert "{PASSWORD}" not in payload["body"]
    assert "{MINUTOS}" not in payload["body"]
    assert message == "Se houver uma conta com este e-mail, enviamos uma senha provisória. Verifique também a caixa de spam."
