from mydemands.services.bootstrap_flow import resolve_startup_decision


def test_valid_session_requires_confirmation(env):
    auth = env["auth"]
    auth.register("user@test.com", "Abcdef1!")
    auth.create_remember_session("user@test.com", ttl_days=1)

    decision = resolve_startup_decision(auth)

    assert decision.state == "confirm_remember"
    assert decision.user_email == "user@test.com"


def test_switch_account_clears_session_and_goes_to_login(env):
    auth = env["auth"]
    auth.register("user@test.com", "Abcdef1!")
    auth.create_remember_session("user@test.com", ttl_days=1)

    assert resolve_startup_decision(auth).state == "confirm_remember"

    auth.logout()

    assert env["sessions"].load_session() is None
    assert resolve_startup_decision(auth).state == "login"
