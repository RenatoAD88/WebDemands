from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

from ai_writing.errors import MissingAPIKeyError

from bootstrap import ensure_storage_root, resolve_storage_root


AI_ERROR_LOG_FILE_NAMES = {
    "openai": "openIA_error.txt",
    "huggingface": "huggingFace_error.txt",
}
DEFAULT_PROVIDER = "openai"
LOG_FOLDER_NAME = "log"


def _normalize_provider(provider: Optional[str]) -> str:
    normalized = str(provider or "").strip().lower()
    return normalized if normalized in AI_ERROR_LOG_FILE_NAMES else DEFAULT_PROVIDER


def _candidate_storage_roots() -> list[str]:
    roots: list[str] = [resolve_storage_root()]

    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        roots.append(os.path.join(local_app_data, "MyDemands"))

    roots.append(os.path.join(os.path.expanduser("~"), ".mydemands"))

    unique: list[str] = []
    for root in roots:
        if root and root not in unique:
            unique.append(root)
    return unique


def ai_log_dir() -> str:
    errors: list[str] = []

    for root in _candidate_storage_roots():
        base_dir = ensure_storage_root(root)
        if not base_dir:
            errors.append(root)
            continue

        path = os.path.join(base_dir, LOG_FOLDER_NAME)
        log_dir = ensure_storage_root(path)
        if log_dir:
            return log_dir

        errors.append(path)

    attempted = ", ".join(errors) if errors else "(sem caminhos)"
    raise OSError(f"Não foi possível criar a pasta de log em nenhum caminho: {attempted}")


def append_ai_error_log(
    message: str,
    traceback_text: str = "",
    context: Optional[Dict[str, Any]] = None,
    provider: Optional[str] = None,
) -> str:
    normalized_provider = _normalize_provider(provider)
    log_filename = AI_ERROR_LOG_FILE_NAMES[normalized_provider]
    log_path = os.path.join(ai_log_dir(), log_filename)
    when = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context_repr = context or {}
    body = [f"[{when}] {message}", f"context={context_repr}"]
    if traceback_text:
        body.append(traceback_text.rstrip())
    body.append("-" * 80)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(body) + "\n")
    return log_path


def log_ai_generation_error(
    exc: Exception,
    context: Optional[Dict[str, Any]] = None,
    traceback_text: str = "",
    provider: Optional[str] = None,
) -> str:
    message = str(exc)
    if isinstance(exc, MissingAPIKeyError) and not message:
        normalized_provider = _normalize_provider(provider)
        message = "Erro de credencial da Hugging Face" if normalized_provider == "huggingface" else "Erro de credencial da OpenAI"
    return append_ai_error_log(message, traceback_text, context, provider=provider)
