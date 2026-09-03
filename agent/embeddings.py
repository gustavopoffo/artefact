"""
Geração de embeddings via OpenAI API.
"""

import httpx

from .config import config


def generate_embedding(text: str) -> list[float]:
    """Gera embedding para um texto usando OpenAI."""
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {config.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.embedding_model,
        "input": text,
        "dimensions": config.embedding_dims,
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            raise RuntimeError(f"OpenAI embedding error: {response.status_code} - {response.text}")

        data = response.json()
        return data["data"][0]["embedding"]
