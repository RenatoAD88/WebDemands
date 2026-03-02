from pathlib import Path

from mydemands.infra.secrets.dpapi_secret_store import WindowsDpapiSecretStore


def test_dpapi_get_invalid_payload_returns_none_and_removes_key(tmp_path: Path):
    storage_file = tmp_path / "secrets.json"
    storage_file.write_text('{"remember_token":"@@not-base64@@"}', encoding="utf-8")

    store = WindowsDpapiSecretStore(storage_file)

    assert store.get("remember_token") is None
    assert store._load() == {}


def test_dpapi_get_unprotect_error_returns_none_and_removes_key(tmp_path: Path, monkeypatch):
    storage_file = tmp_path / "secrets.json"
    store = WindowsDpapiSecretStore(storage_file)
    store.set("remember_token", b"token")

    def _boom(_: bytes) -> bytes:
        raise RuntimeError("dpapi error")

    monkeypatch.setattr(store, "_unprotect", _boom)

    assert store.get("remember_token") is None
    assert store._load() == {}
