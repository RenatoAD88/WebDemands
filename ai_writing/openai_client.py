from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from typing import Optional

from ai_writing.errors import (
    AIRequestTimeoutError,
    AIWritingError,
    MissingAPIKeyError,
    ModelNotFoundError,
    RateLimitError,
)


DEFAULT_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_CONNECTIVITY_URL = "https://api.openai.com/v1/models"


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.5,
        max_new_tokens: int = 150,
        top_p: Optional[float] = None,
        timeout: float = 30.0,
    ):
        self.api_key = (api_key or "").strip()
        self.model = model.strip() or "gpt-4o-mini"
        self.temperature = float(temperature)
        self.max_new_tokens = int(max_new_tokens)
        self.top_p = top_p
        self.timeout = float(timeout)

    @staticmethod
    def sanitize_text(text: str) -> str:
        return (text or "").replace("\x00", " ").strip()[:6000]

    def build_prompt(self, input_text: str, instruction: str, context: Optional[dict]) -> str:
        sanitized = self.sanitize_text(input_text)
        if not sanitized:
            raise AIWritingError("Texto vazio para sugestão.")
        return f"{instruction}\n\nContexto: {context or {}}\n\nTexto:\n{sanitized}"

    def suggest(self, input_text: str, instruction: str, context: Optional[dict] = None) -> str:
        if not self.api_key:
            raise MissingAPIKeyError("Chave da OpenAI não configurada")

        prompt = self.build_prompt(input_text, instruction, context)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Você é um assistente que reescreve textos corporativos em português do Brasil."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_new_tokens,
        }
        if self.top_p is not None:
            payload["top_p"] = float(self.top_p)

        req = urllib.request.Request(
            DEFAULT_OPENAI_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        attempt = 0
        max_attempts = 2
        while True:
            attempt += 1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    raw = json.loads(response.read().decode("utf-8"))
                    break
            except urllib.error.HTTPError as exc:
                if exc.code == HTTPStatus.TOO_MANY_REQUESTS and attempt < max_attempts:
                    retry_after = self._retry_after_seconds(exc)
                    if retry_after is not None and 0 < retry_after <= 5:
                        time.sleep(retry_after)
                        continue

                if exc.code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
                    raise MissingAPIKeyError("Chave da OpenAI inválida ou ausente") from exc
                if exc.code == HTTPStatus.NOT_FOUND:
                    raise ModelNotFoundError("Modelo da OpenAI não encontrado") from exc
                if exc.code == HTTPStatus.TOO_MANY_REQUESTS:
                    raise RateLimitError(self._build_rate_limit_message(exc)) from exc
                raise AIWritingError(f"Falha na API da OpenAI (HTTP {exc.code})") from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                raise AIRequestTimeoutError("Timeout na API da OpenAI") from exc

        choices = raw.get("choices") if isinstance(raw, dict) else None
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict):
                content = str(message.get("content", "")).strip()
                if content:
                    return content
        raise AIWritingError("Resposta sem conteúdo textual.")

    @staticmethod
    def _retry_after_seconds(exc: urllib.error.HTTPError) -> Optional[float]:
        value = exc.headers.get("Retry-After") if exc.headers else None
        if not value:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_rate_limit_message(exc: urllib.error.HTTPError) -> str:
        default = "Limite de requisições da OpenAI atingido"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            return default

        error = payload.get("error") if isinstance(payload, dict) else None
        code = str(error.get("code", "")) if isinstance(error, dict) else ""
        message = str(error.get("message", "")) if isinstance(error, dict) else ""
        text = f"{code} {message}".lower()
        if "insufficient_quota" in text or "quota" in text:
            return "Cota da OpenAI esgotada. Verifique faturamento e limites da conta."
        return default

    def check_connectivity(self) -> None:
        req = urllib.request.Request(
            DEFAULT_CONNECTIVITY_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout):
                return
        except urllib.error.HTTPError as exc:
            if exc.code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
                raise MissingAPIKeyError("Chave da OpenAI inválida ou ausente") from exc
            raise AIWritingError(f"Falha ao validar conectividade OpenAI (HTTP {exc.code})") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise AIRequestTimeoutError("Timeout na API da OpenAI") from exc
