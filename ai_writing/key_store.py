from __future__ import annotations

from ai_writing.config_store import AIConfigStore, OPENAI_PROVIDER


def load_api_key() -> str:
    return AIConfigStore().load_config(provider=OPENAI_PROVIDER).openai_api_key.strip()


def save_api_key(api_key: str) -> None:
    store = AIConfigStore()
    cfg = store.load_config(provider=OPENAI_PROVIDER)
    cfg.openai_api_key = (api_key or "").strip()
    store.save_config(cfg, provider=OPENAI_PROVIDER)


def has_api_key() -> bool:
    return bool(load_api_key())
