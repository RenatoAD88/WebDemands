from mydemands.domain.models import EmailSettings
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


def test_save_final_password_clears_flags(env, monkeypatch):
    env["auth"].register("user@test.com", "Abcdef1!")
    _configure(env)
    monkeypatch.setattr(env["reset"], "_generate_provisional_password", lambda: "Prov_1234567890")

    env["reset"].request_password_reset("user@test.com")
    user = env["users"].get_by_email("user@test.com")
    assert user is not None and user.must_change_password is True

    env["reset"].save_final_password("user@test.com", "Xyzabc1!")

    updated = env["users"].get_by_email("user@test.com")
    assert updated is not None
    assert updated.must_change_password is False
    assert updated.provisional_expires_at is None
    assert updated.provisional_issued_at is None
    assert env["auth"].authenticate("user@test.com", "Xyzabc1!")
