from __future__ import annotations

import importlib.util
from typing import Protocol

from ai_writing.config_store import AIConfig, HUGGINGFACE_PROVIDER, OPENAI_PROVIDER
from ai_writing.errors import AIWritingError


class IAProvider(Protocol):
    def check_connectivity(self) -> None: ...

    def suggest(self, input_text: str, instruction: str, context: dict | None = None) -> str: ...

    def build_prompt(self, input_text: str, instruction: str, context: dict | None) -> str: ...


class AIProviderFactory:
    @staticmethod
    def create(provider: str, cfg: AIConfig) -> IAProvider:
        if provider == HUGGINGFACE_PROVIDER:
            from ai_writing.huggingface_client import HuggingFaceClient

            return HuggingFaceClient(
                api_token=cfg.hf_api_token,
                model=cfg.hf_model,
                temperature=cfg.hf_temperature,
                max_new_tokens=cfg.hf_max_new_tokens,
                top_p=cfg.hf_top_p,
                timeout=cfg.hf_timeout,
            )

        if importlib.util.find_spec("openai") is None:
            raise AIWritingError("Dependência ausente: instale openai para usar o provider OpenAI")

        from ai_writing.openai_client import OpenAIClient

        return OpenAIClient(
            api_key=cfg.openai_api_key,
            model=cfg.openai_model,
            temperature=cfg.openai_temperature,
            max_new_tokens=cfg.openai_max_output_tokens,
        )

    @staticmethod
    def available_providers() -> tuple[str, str]:
        return (OPENAI_PROVIDER, HUGGINGFACE_PROVIDER)
