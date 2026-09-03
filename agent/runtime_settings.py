"""
Configurações runtime do agente (ex.: modelo LLM).

Persistidas em agent_prompts (name=runtime_settings) para sobreviver a redeploys.
Em memória há cache para não bater no banco a cada mensagem.
"""

from __future__ import annotations

import json
from typing import Any

from .config import config, env

ALLOWED_MODELS: list[dict[str, str]] = [
    {"id": "gpt-4o", "label": "GPT-4o (recomendado)"},
    {"id": "gpt-4o-mini", "label": "GPT-4o Mini (mais barato / mais seco)"},
    {"id": "gpt-4.1", "label": "GPT-4.1"},
    {"id": "gpt-4.1-mini", "label": "GPT-4.1 Mini"},
]

ALLOWED_MODEL_IDS = {m["id"] for m in ALLOWED_MODELS}
SETTINGS_PROMPT_NAME = "runtime_settings"
DEFAULT_MODEL = env("LLM_MODEL", "gpt-4o") or "gpt-4o"

_cached_model: str | None = None


def _normalize_model(model: str) -> str:
    model = (model or "").strip()
    if model not in ALLOWED_MODEL_IDS:
        raise ValueError(
            f"Modelo invalido: {model}. Opcoes: {', '.join(sorted(ALLOWED_MODEL_IDS))}"
        )
    return model


def get_llm_model() -> str:
    """Retorna o modelo ativo (cache → banco → env/default)."""
    global _cached_model
    if _cached_model:
        return _cached_model

    from .database import db

    try:
        row = db.get_active_prompt(SETTINGS_PROMPT_NAME)
        if row and row.get("content"):
            data = json.loads(row["content"])
            model = data.get("llm_model")
            if model in ALLOWED_MODEL_IDS:
                _cached_model = model
                return model
    except Exception:
        pass

    fallback = DEFAULT_MODEL if DEFAULT_MODEL in ALLOWED_MODEL_IDS else "gpt-4o"
    # Se config.llm_model for válido e diferente, prioriza env já carregado no Config
    if config.llm_model in ALLOWED_MODEL_IDS:
        fallback = config.llm_model

    _cached_model = fallback
    return fallback


def set_llm_model(model: str) -> str:
    """Define e persiste o modelo ativo. Retorna o id do modelo."""
    global _cached_model
    model = _normalize_model(model)

    from .database import db

    db.upsert_runtime_settings({"llm_model": model})
    _cached_model = model
    return model


def get_settings_payload() -> dict[str, Any]:
    """Payload para o endpoint admin."""
    return {
        "llm_model": get_llm_model(),
        "allowed_models": ALLOWED_MODELS,
        "default_model": "gpt-4o",
    }
