"""
Acesso ao banco de dados Supabase via PostgREST.
"""

import json
from typing import Any
from uuid import UUID
import httpx

from .config import config


class Database:
    """Cliente para o Supabase PostgREST."""

    def __init__(self):
        self.base_url = config.supabase_url
        self.headers = {
            "apikey": config.supabase_key,
            "Authorization": f"Bearer {config.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _request(
        self,
        method: str,
        path: str,
        data: dict | list | None = None,
        params: dict | None = None,
    ) -> list[dict] | dict:
        """Executa requisição HTTP ao PostgREST."""
        url = f"{self.base_url}/{path}"

        with httpx.Client(timeout=30) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
            )

            if response.status_code >= 400:
                raise RuntimeError(f"Supabase error: {response.status_code} - {response.text}")

            if response.text:
                return response.json()
            return {}

    # -------------------------------------------------------------------------
    # Chat Sessions
    # -------------------------------------------------------------------------

    def create_session(self, channel: str = "web", metadata: dict | None = None) -> dict:
        """Cria nova sessão de chat."""
        data = {
            "channel": channel,
            "status": "active",
            "metadata": metadata or {},
        }
        result = self._request("POST", "chat_sessions", data)
        return result[0] if isinstance(result, list) else result

    def get_session(self, session_id: str) -> dict | None:
        """Busca sessão por ID."""
        result = self._request("GET", "chat_sessions", params={
            "session_id": f"eq.{session_id}",
            "select": "*",
        })
        return result[0] if result else None

    def update_session(self, session_id: str, **fields) -> dict:
        """Atualiza campos da sessão."""
        result = self._request("PATCH", "chat_sessions", fields, params={
            "session_id": f"eq.{session_id}",
        })
        return result[0] if isinstance(result, list) else result

    def end_session(self, session_id: str) -> dict:
        """Encerra a sessão."""
        return self.update_session(session_id, status="ended", ended_at="now()")

    # -------------------------------------------------------------------------
    # Chat Messages
    # -------------------------------------------------------------------------

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        model_used: str | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        response_time_ms: int | None = None,
        sources_consulted: dict | None = None,
    ) -> dict:
        """Adiciona mensagem à sessão."""
        data = {
            "session_id": session_id,
            "role": role,
            "content": content,
        }
        if model_used:
            data["model_used"] = model_used
        if tokens_input is not None:
            data["tokens_input"] = tokens_input
        if tokens_output is not None:
            data["tokens_output"] = tokens_output
        if response_time_ms is not None:
            data["response_time_ms"] = response_time_ms
        if sources_consulted is not None:
            data["sources_consulted"] = sources_consulted

        result = self._request("POST", "chat_messages", data)
        return result[0] if isinstance(result, list) else result

    def get_session_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        """Busca mensagens de uma sessão, ordenadas por data."""
        return self._request("GET", "chat_messages", params={
            "session_id": f"eq.{session_id}",
            "select": "message_id,role,content,created_at",
            "order": "created_at.asc",
            "limit": str(limit),
        })

    # -------------------------------------------------------------------------
    # Agent Prompts
    # -------------------------------------------------------------------------

    def get_active_prompt(self, name: str = "system_prompt") -> dict | None:
        """Busca o prompt ativo por nome."""
        result = self._request("GET", "agent_prompts", params={
            "name": f"eq.{name}",
            "is_active": "eq.true",
            "select": "prompt_id,name,content,version,tokens_estimated",
        })
        return result[0] if result else None

    def increment_prompt_usage(self, prompt_id: str) -> None:
        """Incrementa contador de uso do prompt."""
        # Busca valor atual e incrementa
        result = self._request("GET", "agent_prompts", params={
            "prompt_id": f"eq.{prompt_id}",
            "select": "times_used",
        })
        if result:
            current = result[0].get("times_used", 0) or 0
            self._request("PATCH", "agent_prompts",
                {"times_used": current + 1},
                params={"prompt_id": f"eq.{prompt_id}"}
            )

    # -------------------------------------------------------------------------
    # RAG Query Log
    # -------------------------------------------------------------------------

    def log_rag_query(
        self,
        query_text: str,
        query_embedding: list[float],
        chunks_returned: list[str],
        top_similarity: float | None,
        avg_similarity: float | None,
        search_time_ms: int,
        session_id: str | None = None,
    ) -> dict:
        """Registra busca RAG para análise. Retorna o log com log_id."""
        data = {
            "query_text": query_text,
            "query_embedding": query_embedding,
            "chunks_returned": chunks_returned,
            "chunks_count": len(chunks_returned),
            "top_similarity": top_similarity,
            "avg_similarity": avg_similarity,
            "search_time_ms": search_time_ms,
        }
        if session_id:
            data["session_id"] = session_id

        result = self._request("POST", "rag_query_log", data)
        return result[0] if isinstance(result, list) else result

    def update_rag_log_message(self, log_id: str, message_id: str) -> None:
        """Atualiza o message_id no log de RAG após criar a mensagem."""
        self._request("PATCH", "rag_query_log", 
            {"message_id": message_id},
            params={"log_id": f"eq.{log_id}"}
        )

    # -------------------------------------------------------------------------
    # Customers
    # -------------------------------------------------------------------------

    def find_customer_by_email(self, email: str) -> dict | None:
        """Busca cliente por email."""
        result = self._request("GET", "customers", params={
            "email": f"eq.{email}",
            "select": "*",
        })
        return result[0] if result else None

    def find_customer_by_phone(self, phone: str) -> dict | None:
        """Busca cliente por telefone."""
        result = self._request("GET", "customers", params={
            "phone": f"eq.{phone}",
            "select": "*",
        })
        return result[0] if result else None

    def get_customer_orders(self, customer_id: int) -> list[dict]:
        """Busca pedidos de um cliente."""
        return self._request("GET", "v_order_details", params={
            "customer_id": f"eq.{customer_id}",
            "select": "*",
            "order": "order_date.desc",
        })

    # -------------------------------------------------------------------------
    # Products
    # -------------------------------------------------------------------------

    def search_products(self, query: str, limit: int = 5) -> list[dict]:
        """
        Busca produtos por nome.
        Divide a query em palavras e busca produtos que contenham qualquer uma delas.
        """
        # Divide query em palavras significativas (>2 chars)
        words = [w.strip() for w in query.split() if len(w.strip()) > 2]
        
        if not words:
            return []

        all_results = []
        seen_ids = set()

        for word in words:
            results = self._request("GET", "v_products_with_category", params={
                "product_name": f"ilike.*{word}*",
                "select": "product_id,product_name,price_brl,stock_quantity,status,category_name",
                "limit": str(limit * 2),
            })
            for r in results:
                if r["product_id"] not in seen_ids:
                    seen_ids.add(r["product_id"])
                    all_results.append(r)

        # Também busca por categoria
        for word in words:
            results = self._request("GET", "v_products_with_category", params={
                "category_name": f"ilike.*{word}*",
                "status": "eq.active",
                "select": "product_id,product_name,price_brl,stock_quantity,status,category_name",
                "limit": str(limit),
            })
            for r in results:
                if r["product_id"] not in seen_ids:
                    seen_ids.add(r["product_id"])
                    all_results.append(r)

        return all_results[:limit]

    def get_products_by_category(self, category_name: str, limit: int = 10) -> list[dict]:
        """Busca produtos por categoria."""
        return self._request("GET", "v_products_with_category", params={
            "category_name": f"ilike.*{category_name}*",
            "status": "eq.active",
            "select": "product_id,product_name,price_brl,stock_quantity",
            "order": "price_brl.asc",
            "limit": str(limit),
        })

    def get_product_by_id(self, product_id: int) -> dict | None:
        """Busca produto por ID."""
        result = self._request("GET", "v_products_with_category", params={
            "product_id": f"eq.{product_id}",
            "select": "*",
        })
        return result[0] if result else None

    def get_active_promotions(self) -> list[dict]:
        """Busca produtos com promoção ativa."""
        return self._request("GET", "v_products_with_active_promotion", params={
            "select": "product_id,product_name,original_price,discount_percent,discounted_price,promotion_name,category_name",
            "order": "discount_percent.desc",
        })

    def get_low_stock_products(self, threshold: int = 5) -> list[dict]:
        """Busca produtos com estoque baixo."""
        return self._request("GET", "v_inventory_status", params={
            "stock_quantity": f"lte.{threshold}",
            "select": "product_id,product_name,stock_quantity,stock_level,category_name",
            "order": "stock_quantity.asc",
        })

    # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------

    def get_order_by_id(self, order_id: int) -> list[dict]:
        """Busca detalhes de um pedido."""
        return self._request("GET", "v_order_details", params={
            "order_id": f"eq.{order_id}",
            "select": "*",
        })

    def get_order_by_tracking(self, tracking_code: str) -> list[dict]:
        """Busca pedido por código de rastreio."""
        return self._request("GET", "orders", params={
            "tracking_code": f"eq.{tracking_code}",
            "select": "*",
        })


db = Database()
