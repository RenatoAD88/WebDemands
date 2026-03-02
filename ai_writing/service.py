from __future__ import annotations

from typing import Any, Dict

from ai_writing.config_store import AIConfigStore, DEFAULT_PROVIDER
from ai_writing.errors import AIWritingError, UsageLimitReachedError
from ai_writing.provider_factory import AIProviderFactory


class AIWritingService:
    def __init__(self, config_store: AIConfigStore | None = None):
        self.config_store = config_store or AIConfigStore()

    @staticmethod
    def _resolve_client(provider: str, cfg):
        return AIProviderFactory.create(provider, cfg)

    def generate(self, input_text: str, instruction: str, context: Dict[str, Any], provider: str = DEFAULT_PROVIDER) -> str:
        cfg = self.config_store.reset_usage_if_needed(self.config_store.load_config(provider=provider), provider=provider)
        if not cfg.ai_enabled:
            raise AIWritingError("IA desativada")
        if cfg.ia_usage_count >= cfg.ia_usage_limit:
            raise UsageLimitReachedError("Limite mensal de uso da IA atingido")

        current_provider = cfg.ai_provider or provider
        client = self._resolve_client(current_provider, cfg)

        model = cfg.openai_model if current_provider == "openai" else cfg.hf_model
        temp = cfg.openai_temperature if current_provider == "openai" else cfg.hf_temperature

        prompt = client.build_prompt(input_text=input_text, instruction=instruction, context=context)
        cache_key = self.config_store.build_cache_key(prompt, model, temp)

        if cfg.ia_cache_enabled:
            cached = self.config_store.get_cached_response(cache_key, provider=current_provider)
            if cached:
                return cached

        response = client.suggest(input_text=input_text, instruction=instruction, context=context)
        if cfg.ia_cache_enabled:
            self.config_store.save_cache_response(cache_key, response, provider=current_provider)
        self.config_store.increment_usage(cfg, provider=provider)
        return response
