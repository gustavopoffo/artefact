"""
Interface com a LLM (OpenAI GPT).
"""

import time
import httpx

from .config import config


class LLM:
    """Cliente para OpenAI Chat Completions."""

    def __init__(self, model: str | None = None):
        self.model = model or config.llm_model
        self.api_key = config.openai_api_key

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> tuple[str, dict]:
        """
        Envia mensagens para a LLM e retorna resposta.

        Retorna:
            - Texto da resposta
            - Métricas (model, tokens, tempo)
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.perf_counter()

        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers=headers, json=payload)

            if response.status_code >= 400:
                raise RuntimeError(f"LLM error: {response.status_code} - {response.text}")

            data = response.json()

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        metrics = {
            "model_used": self.model,
            "tokens_input": usage.get("prompt_tokens", 0),
            "tokens_output": usage.get("completion_tokens", 0),
            "response_time_ms": elapsed_ms,
        }

        return content, metrics


llm = LLM()
