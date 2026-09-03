"""
Interface com a LLM (OpenAI GPT).
"""

import time
import httpx

from .config import config


class LLM:
    """Cliente para OpenAI Chat Completions (conexão reutilizada)."""

    def __init__(self, model: str | None = None):
        self.model = model or config.llm_model
        self.api_key = config.openai_api_key
        # Keep-alive: evita TLS/handshake novo a cada mensagem (~ganho de latência)
        self._client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.6,
        max_tokens: int = 500,
        model: str | None = None,
    ) -> tuple[str, dict]:
        """
        Envia mensagens para a LLM e retorna resposta.

        Retorna:
            - Texto da resposta
            - Métricas (model, tokens, tempo)
        """
        used_model = model or self.model
        payload = {
            "model": used_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.perf_counter()
        response = self._client.post("/chat/completions", json=payload)

        if response.status_code >= 400:
            raise RuntimeError(f"LLM error: {response.status_code} - {response.text}")

        data = response.json()
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        metrics = {
            "model_used": used_model,
            "tokens_input": usage.get("prompt_tokens", 0),
            "tokens_output": usage.get("completion_tokens", 0),
            "response_time_ms": elapsed_ms,
        }

        return content, metrics


llm = LLM()
