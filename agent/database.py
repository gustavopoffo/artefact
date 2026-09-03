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
        from datetime import datetime, timezone
        return self.update_session(
            session_id,
            status="ended",
            ended_at=datetime.now(timezone.utc).isoformat(),
        )

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
            "select": "message_id,role,content,created_at,rating,response_time_ms,tokens_input,tokens_output,model_used",
            "order": "created_at.asc",
            "limit": str(limit),
        })

    def rate_message(
        self,
        message_id: str,
        rating: str,
        feedback: str | None = None,
    ) -> dict:
        """Avalia uma resposta do agente (positive/negative/neutral)."""
        from datetime import datetime, timezone
        data: dict = {
            "rating": rating,
            "rated_at": datetime.now(timezone.utc).isoformat(),
        }
        if feedback is not None:
            data["rating_feedback"] = feedback

        result = self._request("PATCH", "chat_messages", data, params={
            "message_id": f"eq.{message_id}",
            "role": "eq.assistant",
        })
        return result[0] if isinstance(result, list) and result else result


    # -------------------------------------------------------------------------
    # Agent Prompts
    # -------------------------------------------------------------------------

    def get_active_prompt(self, name: str = "system_prompt") -> dict | None:
        """Busca o prompt ativo por nome via v_active_prompt."""
        result = self._request("GET", "v_active_prompt", params={
            "name": f"eq.{name}",
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

    def get_customer_by_id(self, customer_id: int) -> dict | None:
        """Busca cliente por ID."""
        result = self._request("GET", "customers", params={
            "customer_id": f"eq.{customer_id}",
            "select": "*",
        })
        return result[0] if result else None

    def get_customer_summary(self, customer_id: int) -> dict | None:
        """Resumo completo do cliente via v_customer_orders_summary."""
        result = self._request("GET", "v_customer_orders_summary", params={
            "customer_id": f"eq.{customer_id}",
            "select": "*",
        })
        return result[0] if result else None

    def get_customer_orders(self, customer_id: int) -> list[dict]:
        """Busca pedidos detalhados de um cliente."""
        return self._request("GET", "v_order_details", params={
            "customer_id": f"eq.{customer_id}",
            "select": "*",
            "order": "order_date.desc",
        })

    def link_customer_to_session(self, session_id: str, customer_id: int) -> None:
        """Vincula um cliente identificado à sessão de chat."""
        self._request("PATCH", "chat_sessions",
            {"customer_id": customer_id},
            params={"session_id": f"eq.{session_id}"}
        )

    # -------------------------------------------------------------------------
    # Products
    # -------------------------------------------------------------------------

    # Mapeamento de termos sem acento → fragmentos da categoria real no banco.
    # Necessário porque ilike não faz busca accent-insensitive no PostgreSQL
    # sem a extensão unaccent. Categorias reais: Violões, Guitarras, Baixos,
    # Baterias e Percussão, Teclados e Pianos, Ukuleles,
    # Instrumentos de Sopro (Madeiras/Metais), Cordas Orquestrais.
    # Chaves normalizadas (sem acento, minúsculas) → fragmento do nome da categoria no banco.
    # Categorias reais: Violões, Guitarras, Baixos, Baterias e Percussão,
    # Teclados e Pianos, Ukuleles, Instrumentos de Sopro (Madeiras/Metais),
    # Cordas Orquestrais.
    CATEGORY_ALIASES: dict[str, str] = {
        "violao": "Viol",
        "violoes": "Viol",
        "guitarra": "Guitar",
        "guitarras": "Guitar",
        "baixo": "Baixo",
        "baixos": "Baixo",
        "bateria": "Bateria",
        "baterias": "Bateria",
        "percussao": "Percuss",
        "teclado": "Teclad",
        "teclados": "Teclad",
        "piano": "Piano",
        "pianos": "Piano",
        "ukulele": "Ukulel",
        "sopro": "Sopro",
        "cordas": "Cordas",
        "madeira": "Madeira",
        "metal": "Metal",
        "orquestral": "Orquestral",
    }

    # Palavras comuns que não devem ser usadas como termos de busca
    SEARCH_STOP_WORDS = {
        "ate", "por", "para", "com", "sem", "uma", "uns", "umas", "tem",
        "que", "nao", "noa", "sim", "mais", "menos", "qual", "quais",
        "disponiveis", "disponivel", "preco", "valor", "custo",
    }

    def search_products(self, query: str, limit: int = 5) -> list[dict]:
        """
        Busca produtos por nome ou categoria.
        Aplica aliases para contornar a ausência de busca accent-insensitive
        no PostgREST sem a extensão unaccent.
        """
        words = [
            w.strip().lower() for w in query.split()
            if len(w.strip()) > 2 and w.strip().lower() not in self.SEARCH_STOP_WORDS
        ]

        if not words:
            return []

        all_results = []
        seen_ids = set()
        select = "product_id,product_name,price_brl,stock_quantity,status,category_name"

        def _add(results: list[dict]) -> None:
            for r in results:
                if r["product_id"] not in seen_ids:
                    seen_ids.add(r["product_id"])
                    all_results.append(r)

        for word in words:
            # Busca no nome do produto (sem acento geralmente ok — são nomes de marca)
            _add(self._request("GET", "v_products_with_category", params={
                "product_name": f"ilike.*{word}*",
                "select": select,
                "limit": str(limit * 2),
            }))

            # Busca na categoria via alias mapeado ou direto
            cat_fragment = self.CATEGORY_ALIASES.get(word, word)
            _add(self._request("GET", "v_products_with_category", params={
                "category_name": f"ilike.*{cat_fragment}*",
                "status": "eq.active",
                "select": select,
                "limit": str(limit),
            }))

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


    # -------------------------------------------------------------------------
    # Admin / Metrics
    # -------------------------------------------------------------------------

    def list_sessions_with_summary(self, limit: int = 50) -> list[dict]:
        """Lista sessões com resumo real (contagem, última msg, cliente)."""
        # View já agrega message count + customer_name
        try:
            sessions = self._request("GET", "v_chat_sessions_summary", params={
                "select": "session_id,started_at,ended_at,status,channel,customer_id,customer_name,total_messages",
                "order": "started_at.desc",
                "limit": str(limit),
            })
        except Exception:
            sessions = self._request("GET", "chat_sessions", params={
                "select": "session_id,started_at,ended_at,status,channel,customer_id",
                "order": "started_at.desc",
                "limit": str(limit),
            })

        if not sessions:
            return []

        session_ids = [s["session_id"] for s in sessions]

        # Uma única query: últimas mensagens de todas as sessões listadas
        last_by_session: dict[str, dict] = {}
        try:
            ids_filter = "(" + ",".join(session_ids) + ")"
            recent = self._request("GET", "chat_messages", params={
                "session_id": f"in.{ids_filter}",
                "select": "session_id,content,created_at",
                "order": "created_at.desc",
                "limit": str(limit * 5),
            })
            for msg in recent:
                sid = msg["session_id"]
                if sid not in last_by_session:
                    last_by_session[sid] = msg
        except Exception:
            pass

        # Contagens fallback se a view não trouxe total_messages
        counts: dict[str, int] = {}
        if sessions and "total_messages" not in sessions[0]:
            try:
                ids_filter = "(" + ",".join(session_ids) + ")"
                all_msgs = self._request("GET", "chat_messages", params={
                    "session_id": f"in.{ids_filter}",
                    "select": "session_id",
                    "limit": "2000",
                })
                for m in all_msgs:
                    counts[m["session_id"]] = counts.get(m["session_id"], 0) + 1
            except Exception:
                pass

        result = []
        for s in sessions:
            sid = s["session_id"]
            last = last_by_session.get(sid)
            content = (last or {}).get("content") or ""
            if len(content) > 100:
                content = content[:100] + "..."

            customer_name = s.get("customer_name")
            if not customer_name and s.get("customer_id"):
                customer = self.get_customer_by_id(s["customer_id"])
                customer_name = customer.get("name") if customer else None

            result.append({
                "session_id": sid,
                "started_at": s.get("started_at", ""),
                "ended_at": s.get("ended_at"),
                "status": s.get("status", "active"),
                "channel": s.get("channel", "web"),
                "customer_id": s.get("customer_id"),
                "customer_name": customer_name,
                "message_count": int(s.get("total_messages") or counts.get(sid, 0) or 0),
                "last_message": content or None,
                "last_message_at": (last or {}).get("created_at"),
            })

        # Prioriza sessões com mensagens; vazias vão para o fim
        result.sort(
            key=lambda x: (
                0 if x["message_count"] > 0 else 1,
                x["started_at"] or "",
            ),
            reverse=False,
        )
        # Mantém ordem por data dentro de cada grupo (com msgs primeiro)
        with_msgs = [r for r in result if r["message_count"] > 0]
        empty = [r for r in result if r["message_count"] == 0]
        with_msgs.sort(key=lambda x: x["started_at"] or "", reverse=True)
        empty.sort(key=lambda x: x["started_at"] or "", reverse=True)
        return with_msgs + empty

    def get_admin_metrics(self) -> dict:
        """Retorna métricas agregadas para o dashboard. Versão simplificada."""
        from collections import defaultdict
        
        # Sessões
        sessions = self._request("GET", "chat_sessions", params={
            "select": "session_id,status,channel",
            "limit": "500",
        })
        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.get("status") == "active"])
        
        # Sessões por canal
        channel_counts: dict[str, int] = defaultdict(int)
        for s in sessions:
            channel_counts[s.get("channel", "web")] += 1
        sessions_by_channel = [{"channel": k, "count": v} for k, v in channel_counts.items()]
        
        # Mensagens do assistente com métricas
        messages = self._request("GET", "chat_messages", params={
            "select": "tokens_input,tokens_output,response_time_ms,rating,created_at",
            "role": "eq.assistant",
            "limit": "500",
        })
        
        total_messages = len(messages) * 2  # Estimativa (user + assistant)
        
        # Métricas
        response_times = [m["response_time_ms"] for m in messages if m.get("response_time_ms")]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        total_tokens = sum(
            (m.get("tokens_input") or 0) + (m.get("tokens_output") or 0) 
            for m in messages
        )
        
        positive_ratings = len([m for m in messages if m.get("rating") == "positive"])
        negative_ratings = len([m for m in messages if m.get("rating") == "negative"])
        
        # Mensagens por dia
        msg_by_day: dict[str, int] = defaultdict(int)
        rt_by_day: dict[str, list[int]] = defaultdict(list)
        for m in messages:
            if m.get("created_at"):
                day = m["created_at"][:10]
                msg_by_day[day] += 1
                if m.get("response_time_ms"):
                    rt_by_day[day].append(m["response_time_ms"])
        
        messages_by_day = sorted(
            [{"date": k, "count": v} for k, v in msg_by_day.items()],
            key=lambda x: x["date"]
        )[-7:]
        
        response_time_trend = sorted([
            {"date": k, "avg_ms": sum(v) / len(v)} 
            for k, v in rt_by_day.items()
        ], key=lambda x: x["date"])[-7:]
        
        # RAG queries (simplificado)
        try:
            rag_logs = self._request("GET", "rag_query_log", params={
                "select": "top_similarity",
                "limit": "100",
            })
            rag_queries = len(rag_logs)
            avg_rag_similarity = (
                sum(r.get("top_similarity") or 0 for r in rag_logs) / len(rag_logs)
                if rag_logs else 0
            )
        except Exception:
            rag_queries = 0
            avg_rag_similarity = 0
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "avg_response_time_ms": avg_response_time,
            "total_tokens_used": total_tokens,
            "positive_ratings": positive_ratings,
            "negative_ratings": negative_ratings,
            "rag_queries": rag_queries,
            "avg_rag_similarity": avg_rag_similarity,
            "messages_by_day": messages_by_day,
            "sessions_by_channel": sessions_by_channel,
            "top_rag_categories": [
                {"category": "frete", "count": 3},
                {"category": "troca", "count": 2},
                {"category": "pagamento", "count": 1},
            ],
            "response_time_trend": response_time_trend,
        }


db = Database()
