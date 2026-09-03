"""
Geração de embeddings via OpenAI API.
"""

import httpx

from .config import config


_client = httpx.Client(
    base_url="https://api.openai.com/v1",
    headers={
        "Authorization": f"Bearer {config.openai_api_key}",
        "Content-Type": "application/json",
    },
    timeout=httpx.Timeout(30.0, connect=10.0),
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
)


def generate_embedding(text: str) -> list[float]:
    """Gera embedding para um texto usando OpenAI."""
    payload = {
        "model": config.embedding_model,
        "input": text,
        "dimensions": config.embedding_dims,
    }

    response = _client.post("/embeddings", json=payload)

    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI embedding error: {response.status_code} - {response.text}")

    data = response.json()
    return data["data"][0]["embedding"]
