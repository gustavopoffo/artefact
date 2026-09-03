"""
Agente de chat — orquestra todo o fluxo de conversa.
"""

import re
from dataclasses import dataclass, field

from .database import db
from .rag import rag
from .llm import llm


@dataclass
class AgentResponse:
    """Resposta do agente com métricas."""
    content: str
    message_id: str
    model_used: str
    tokens_input: int
    tokens_output: int
    response_time_ms: int
    sources_consulted: dict
    rag_chunks_used: int


class Agent:
    """
    Agente conversacional do Empório da Música.
    
    Fluxo:
    1. Carrega system prompt do banco
    2. Busca contexto RAG se necessário
    3. Consulta dados do banco se necessário
    4. Gera resposta via LLM
    5. Registra tudo para métricas
    """

    def __init__(self, session_id: str | None = None, channel: str = "web"):
        self.session_id = session_id
        self.channel = channel
        self.system_prompt: str | None = None
        self.prompt_id: str | None = None
        self._initialized = False

    def _initialize(self) -> None:
        """Inicializa sessão e carrega prompt."""
        if self._initialized:
            return

        # Cria sessão se não existir
        if not self.session_id:
            session = db.create_session(channel=self.channel)
            self.session_id = session["session_id"]

        # Carrega system prompt ativo
        prompt = db.get_active_prompt("system_prompt")
        if not prompt:
            raise RuntimeError("Nenhum system_prompt ativo encontrado")

        self.system_prompt = prompt["content"]
        self.prompt_id = prompt["prompt_id"]
        self._initialized = True

    def _detect_intent(self, message: str) -> dict:
        """
        Detecta a intenção da mensagem para decidir o que buscar.
        Retorna dicionário com flags.
        """
        message_lower = message.lower()

        intent = {
            "needs_product_search": False,
            "needs_rag": False,
            "rag_category": None,
            "product_query": None,
            "needs_order_lookup": False,
            "order_id": None,
            "tracking_code": None,
        }

        # Busca de produto
        product_patterns = [
            r"tem\s+(.+?)(\?|$)",
            r"vocês?\s+têm\s+(.+?)(\?|$)",
            r"procuro\s+(.+?)(\?|$)",
            r"quero\s+(.+?)(\?|$)",
            r"preço\s+d[oa]\s+(.+?)(\?|$)",
            r"quanto\s+custa\s+(.+?)(\?|$)",
            r"estoque\s+d[oa]\s+(.+?)(\?|$)",
        ]
        for pattern in product_patterns:
            match = re.search(pattern, message_lower)
            if match:
                intent["needs_product_search"] = True
                intent["product_query"] = match.group(1).strip()
                break

        # Categorias de instrumentos
        categories = ["guitarra", "violao", "baixo", "ukulele", "teclado", "bateria", "sopro"]
        for cat in categories:
            if cat in message_lower:
                intent["needs_product_search"] = True
                if not intent["product_query"]:
                    intent["product_query"] = cat

        # RAG - políticas
        rag_triggers = {
            "pagamento": ["pagar", "parcela", "cartao", "pix", "boleto", "pagamento", "credito", "debito"],
            "troca": ["trocar", "troca", "devolver", "devolucao", "arrependimento", "defeito"],
            "frete": ["frete", "entrega", "envio", "prazo", "correios", "sedex", "rastreio", "rastrear"],
            "promocao": ["promocao", "desconto", "black friday", "oferta", "liquidacao"],
            "garantia": ["garantia", "defeito", "conserto", "assistencia"],
            "lgpd": ["dados", "privacidade", "lgpd", "excluir meus dados", "cadastro"],
        }
        for category, keywords in rag_triggers.items():
            if any(kw in message_lower for kw in keywords):
                intent["needs_rag"] = True
                intent["rag_category"] = category
                break

        # Pedido
        order_match = re.search(r"pedido\s*#?\s*(\d+)", message_lower)
        if order_match:
            intent["needs_order_lookup"] = True
            intent["order_id"] = int(order_match.group(1))

        # Rastreio
        tracking_match = re.search(r"(BR[A-Z0-9]{9,}BR)", message.upper())
        if tracking_match:
            intent["needs_order_lookup"] = True
            intent["tracking_code"] = tracking_match.group(1)

        return intent

    def _gather_context(self, message: str, intent: dict) -> tuple[str, dict]:
        """
        Reúne contexto necessário (RAG + banco) para a resposta.
        Retorna contexto formatado e sources_consulted.
        """
        context_parts = []
        sources = {"tables": [], "chunks": [], "rag_metrics": None}

        # RAG - políticas
        if intent["needs_rag"]:
            chunks, metrics = rag.search(
                message,
                filter_category=intent.get("rag_category"),
            )
            if chunks:
                context_parts.append(rag.format_context(chunks))
                sources["chunks"] = [c["chunk_id"] for c in chunks]
                sources["rag_metrics"] = metrics

                # Loga busca RAG
                db.log_rag_query(
                    query_text=message,
                    chunks_returned=sources["chunks"],
                    top_similarity=metrics.get("top_similarity"),
                    avg_similarity=metrics.get("avg_similarity"),
                    search_time_ms=metrics.get("search_time_ms", 0),
                    session_id=self.session_id,
                )

        # Busca de produtos
        if intent["needs_product_search"] and intent["product_query"]:
            products = db.search_products(intent["product_query"])
            if products:
                sources["tables"].append("products")
                lines = ["## Produtos Encontrados\n"]
                for p in products:
                    stock_status = "disponivel" if p["stock_quantity"] > 0 else "ESGOTADO"
                    lines.append(
                        f"- **{p['product_name']}** ({p['category_name']}): "
                        f"R$ {p['price_brl']:.2f} | Estoque: {p['stock_quantity']} ({stock_status})"
                    )
                context_parts.append("\n".join(lines))

            # Verifica promoções
            promos = db.get_active_promotions()
            matching_promos = [
                p for p in promos
                if intent["product_query"].lower() in p["product_name"].lower()
            ]
            if matching_promos:
                sources["tables"].append("promotions")
                lines = ["\n## Promocoes Ativas\n"]
                for p in matching_promos:
                    lines.append(
                        f"- **{p['product_name']}**: de R$ {p['original_price']:.2f} "
                        f"por R$ {p['discounted_price']:.2f} ({p['discount_percent']:.0f}% OFF) "
                        f"— {p['promotion_name']}"
                    )
                context_parts.append("\n".join(lines))

        # Busca de pedido
        if intent["needs_order_lookup"]:
            if intent["order_id"]:
                order_details = db.get_order_by_id(intent["order_id"])
                if order_details:
                    sources["tables"].append("orders")
                    o = order_details[0]
                    lines = [
                        f"\n## Pedido #{o['order_id']}\n",
                        f"- **Cliente:** {o['customer_name']}",
                        f"- **Data:** {o['order_date']}",
                        f"- **Status:** {o['order_status']}",
                        f"- **Total:** R$ {o['total_brl']:.2f}",
                        f"- **Pagamento:** {o['payment_method']}",
                    ]
                    if o.get("tracking_code"):
                        lines.append(f"- **Rastreio:** {o['tracking_code']}")
                    if o.get("estimated_delivery"):
                        lines.append(f"- **Previsao de entrega:** {o['estimated_delivery']}")

                    lines.append("\n**Itens:**")
                    for item in order_details:
                        lines.append(f"  - {item['quantity']}x {item['product_name']}")

                    context_parts.append("\n".join(lines))

            if intent["tracking_code"]:
                orders = db.get_order_by_tracking(intent["tracking_code"])
                if orders:
                    sources["tables"].append("orders")
                    o = orders[0]
                    context_parts.append(
                        f"\n## Rastreio {intent['tracking_code']}\n"
                        f"- Pedido #{o['order_id']}\n"
                        f"- Status: {o['status']}\n"
                        f"- Previsao: {o.get('estimated_delivery', 'nao informada')}"
                    )

        return "\n\n".join(context_parts), sources

    def _build_messages(
        self,
        user_message: str,
        context: str,
        history: list[dict],
    ) -> list[dict]:
        """Monta lista de mensagens para a LLM."""
        messages = []

        # System prompt
        system_content = self.system_prompt
        if context:
            system_content += f"\n\n---\n\n{context}"

        messages.append({"role": "system", "content": system_content})

        # Histórico
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        # Mensagem atual
        messages.append({"role": "user", "content": user_message})

        return messages

    def chat(self, message: str) -> AgentResponse:
        """
        Processa mensagem do usuário e retorna resposta.
        
        Este é o método principal que orquestra todo o fluxo.
        """
        self._initialize()

        # 1. Registra mensagem do usuário
        db.add_message(self.session_id, role="user", content=message)

        # 2. Detecta intenção
        intent = self._detect_intent(message)

        # 3. Reúne contexto (RAG + banco)
        context, sources = self._gather_context(message, intent)

        # 4. Busca histórico da sessão
        history = db.get_session_messages(self.session_id)
        # Remove a mensagem que acabamos de adicionar (já vai no final)
        history = [m for m in history if m["content"] != message][-10:]

        # 5. Monta mensagens para a LLM
        messages = self._build_messages(message, context, history)

        # 6. Chama a LLM
        response_content, llm_metrics = llm.chat(messages)

        # 7. Registra resposta do agente
        assistant_msg = db.add_message(
            session_id=self.session_id,
            role="assistant",
            content=response_content,
            model_used=llm_metrics["model_used"],
            tokens_input=llm_metrics["tokens_input"],
            tokens_output=llm_metrics["tokens_output"],
            response_time_ms=llm_metrics["response_time_ms"],
            sources_consulted=sources,
        )

        return AgentResponse(
            content=response_content,
            message_id=assistant_msg["message_id"],
            model_used=llm_metrics["model_used"],
            tokens_input=llm_metrics["tokens_input"],
            tokens_output=llm_metrics["tokens_output"],
            response_time_ms=llm_metrics["response_time_ms"],
            sources_consulted=sources,
            rag_chunks_used=len(sources.get("chunks", [])),
        )

    def get_session_id(self) -> str:
        """Retorna o ID da sessão atual."""
        self._initialize()
        return self.session_id
