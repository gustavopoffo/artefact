"""
Agente de chat — orquestra todo o fluxo de conversa.
"""

import re
import unicodedata
from dataclasses import dataclass

from .database import db
from .rag import rag
from .llm import llm


def _normalize(text: str) -> str:
    """Remove acentos e coloca em minúsculas para comparações robustas."""
    return unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode("ascii")


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
    customer_identified: bool


class Agent:
    """
    Agente conversacional do Empório da Música.

    Estado interno por sessão:
    - session_id: UUID da sessão no banco
    - customer_id: preenchido quando o cliente se identifica
    - customer: dados completos do cliente identificado

    Fluxo:
    1. Inicia sessão (customer_id = NULL)
    2. Carrega system prompt ativo via v_active_prompt
    3. Detecta intenção da mensagem
    4. Tenta identificar o cliente (email/telefone)
    5. Busca contexto RAG + dados do banco
    6. Gera resposta via LLM
    7. Registra tudo para métricas
    """

    def __init__(self, session_id: str | None = None, channel: str = "web"):
        self.session_id = session_id
        self.channel = channel
        self.system_prompt: str | None = None
        self.prompt_id: str | None = None
        self.customer_id: int | None = None
        self.customer: dict | None = None
        self._initialized = False

    def _initialize(self) -> None:
        """Inicializa sessão, restaura cliente vinculado e carrega prompt."""
        if self._initialized:
            return

        if not self.session_id:
            session = db.create_session(channel=self.channel)
            self.session_id = session["session_id"]
        else:
            # Reabre sessão existente (ex.: chamada via API) e restaura cliente
            session = db.get_session(self.session_id)
            if not session:
                raise ValueError(f"Sessao nao encontrada: {self.session_id}")
            if session.get("customer_id") and not self.customer_id:
                self.customer_id = session["customer_id"]
                self.customer = db.get_customer_by_id(self.customer_id)

        prompt = db.get_active_prompt("system_prompt")
        if not prompt:
            raise RuntimeError("Nenhum system_prompt ativo encontrado")

        self.system_prompt = prompt["content"]
        self.prompt_id = prompt["prompt_id"]
        self._initialized = True

    # -------------------------------------------------------------------------
    # Identificação do cliente
    # -------------------------------------------------------------------------

    def _extract_contact(self, message: str) -> dict:
        """
        Tenta extrair email ou telefone da mensagem.
        Retorna dict com 'email' e/ou 'phone' encontrados.
        """
        contact = {}

        email_match = re.search(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            message
        )
        if email_match:
            contact["email"] = email_match.group(0).lower()

        phone_match = re.search(
            r"\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}",
            message
        )
        if phone_match:
            raw = re.sub(r"[^\d]", "", phone_match.group(0))
            contact["phone"] = f"({raw[:2]}) {raw[2:7]}-{raw[7:]}" if len(raw) == 11 else phone_match.group(0)

        return contact

    def _identify_customer(self, message: str) -> dict | None:
        """
        Tenta identificar o cliente pela mensagem.
        Se encontrar, vincula à sessão e carrega o resumo.
        Retorna o customer encontrado ou None.
        """
        # Já identificado anteriormente nesta sessão
        if self.customer_id:
            return self.customer

        contact = self._extract_contact(message)
        customer = None

        if "email" in contact:
            customer = db.find_customer_by_email(contact["email"])
        if not customer and "phone" in contact:
            customer = db.find_customer_by_phone(contact["phone"])

        if customer:
            self.customer_id = customer["customer_id"]
            self.customer = customer
            db.link_customer_to_session(self.session_id, self.customer_id)

        return customer

    def _format_customer_context(self, customer: dict) -> str:
        """
        Formata o contexto do cliente identificado para incluir no prompt.
        Usa v_customer_orders_summary para personalizar o atendimento.
        """
        summary = db.get_customer_summary(customer["customer_id"])

        lines = [
            "## Cliente Identificado\n",
            f"- **Nome:** {customer['name']}",
            f"- **Cidade:** {customer.get('city', 'nao informada')}",
            f"- **Email:** {customer.get('email', 'nao informado')}",
        ]

        if summary:
            lines += [
                f"- **Total de pedidos:** {summary['total_orders']}",
                f"- **Pedidos entregues:** {summary['delivered_orders']}",
                f"- **Total gasto:** R$ {summary['total_spent']:.2f}",
            ]
            if summary.get("last_order_date"):
                lines.append(f"- **Ultimo pedido:** {summary['last_order_date']}")
        else:
            lines.append("- **Historico:** nenhum pedido registrado")

        lines.append(
            "\nUse o nome do cliente na saudacao. "
            "Se tiver pedidos, pode referenciar o historico se relevante."
        )

        return "\n".join(lines)

    def _format_unknown_visitor_hint(self, contact: dict) -> str:
        """
        Retorna hint para o agente quando o contato informado não está cadastrado.
        """
        identifier = contact.get("email") or contact.get("phone", "")
        return (
            f"## Visitante Nao Cadastrado\n\n"
            f"O contato informado ({identifier}) nao consta em nossa base de clientes. "
            f"Informe ao cliente que ele pode fazer uma compra normalmente e que o cadastro "
            f"sera feito no momento da finalizacao do pedido, ou sugerir que entre em contato "
            f"pelo WhatsApp (67) 3341-4444 para suporte completo."
        )

    # -------------------------------------------------------------------------
    # Detecção de intenção
    # -------------------------------------------------------------------------

    def _detect_intent(self, message: str) -> dict:
        """
        Detecta a intenção da mensagem para decidir o que buscar.
        """
        msg_norm = _normalize(message)

        intent = {
            "needs_product_search": False,
            "needs_rag": False,
            "rag_category": None,
            "product_query": None,
            "needs_order_lookup": False,
            "order_id": None,
            "tracking_code": None,
            "needs_customer_history": False,
        }

        brands = [
            "yamaha", "fender", "crafter", "tagima", "giannini", "rozini",
            "pearl", "ibanez", "takamine", "kala", "memphis", "cort",
            "epiphone", "gibson", "stratocaster", "telecaster",
        ]
        categories = [
            "violao", "violoes", "guitarra", "guitarras", "baixo", "baixos",
            "ukulele", "teclado", "teclados", "piano", "pianos",
            "bateria", "baterias", "sopro", "cordas",
        ]
        query_stop = {
            "quantas", "quantos", "quanto", "quais", "qual", "voce", "voces",
            "tem", "tinha", "estoque", "disponivel", "disponiveis", "unidade",
            "unidades", "da", "de", "do", "das", "dos", "em", "no", "na",
            "uma", "um", "me", "diz", "sobre", "quero", "saber",
        }

        # 1) Marcas/modelos primeiro (evita capturar "em estoque" como produto)
        for brand in brands:
            if brand in msg_norm:
                intent["needs_product_search"] = True
                intent["product_query"] = brand
                break

        # 2) Categorias
        if not intent["product_query"]:
            for cat in categories:
                if cat in msg_norm:
                    intent["needs_product_search"] = True
                    intent["product_query"] = cat
                    break

        # 3) Regex para produto específico
        if not intent["product_query"]:
            product_patterns = [
                r"procuro\s+(.+?)(\?|$)",
                r"quero\s+comprar\s+(.+?)(\?|$)",
                r"preco\s+d[oa]\s+(.+?)(\?|$)",
                r"quanto\s+custa\s+(?:o|a)?\s*(.+?)(\?|$)",
                r"estoque\s+d[oa]\s+(.+?)(\?|$)",
                r"tem\s+(?:o|a)?\s*(.+?)(\?|$)",
            ]
            for pattern in product_patterns:
                match = re.search(pattern, msg_norm)
                if match:
                    raw = match.group(1).strip()
                    cleaned = " ".join(
                        w for w in raw.split()
                        if w not in query_stop and len(w) > 2
                    )
                    if cleaned:
                        intent["needs_product_search"] = True
                        intent["product_query"] = cleaned
                        break

        # 4) Estoque sem marca clara → extrai tokens úteis
        stock_triggers = ["estoque", "disponivel", "quantas", "quantos", "unidade"]
        if not intent["product_query"] and any(t in msg_norm for t in stock_triggers):
            tokens = [
                w for w in re.findall(r"[a-z0-9]+", msg_norm)
                if w not in query_stop and len(w) > 2
            ]
            if tokens:
                intent["needs_product_search"] = True
                intent["product_query"] = " ".join(tokens[:4])

        rag_triggers = {
            "pagamento": ["pagar", "parcela", "cartao", "pix", "boleto", "pagamento", "credito", "debito"],
            "troca": ["trocar", "troca", "devolver", "devolucao", "arrependimento", "defeito"],
            "frete": ["frete", "entrega", "envio", "prazo", "correios", "sedex", "rastreio", "rastrear"],
            "promocao": ["promocao", "desconto", "black friday", "oferta", "liquidacao"],
            "garantia": ["garantia", "defeito", "conserto", "assistencia"],
            "lgpd": ["dados", "privacidade", "lgpd", "excluir meus dados"],
        }
        for rag_cat, keywords in rag_triggers.items():
            if any(kw in msg_norm for kw in keywords):
                intent["needs_rag"] = True
                intent["rag_category"] = rag_cat
                break

        order_match = re.search(r"pedido\s*#?\s*(\d+)", msg_norm)
        if order_match:
            intent["needs_order_lookup"] = True
            intent["order_id"] = int(order_match.group(1))

        tracking_match = re.search(r"(BR[A-Z0-9]{9,}BR)", message.upper())
        if tracking_match:
            intent["needs_order_lookup"] = True
            intent["tracking_code"] = tracking_match.group(1)

        history_keywords = ["meus pedidos", "meu historico", "ja comprei", "ultima compra", "minhas compras"]
        if any(kw in msg_norm for kw in history_keywords):
            intent["needs_customer_history"] = True

        return intent

    # -------------------------------------------------------------------------
    # Contexto
    # -------------------------------------------------------------------------

    def _gather_context(self, message: str, intent: dict, customer: dict | None, unknown_contact: dict) -> tuple[str, dict]:
        """
        Reúne contexto necessário para a resposta.
        Retorna contexto formatado e sources_consulted.
        """
        context_parts = []
        sources = {"tables": [], "chunks": [], "rag_metrics": None, "rag_log_id": None}

        # Contexto do cliente identificado
        if customer:
            context_parts.append(self._format_customer_context(customer))
            sources["tables"].append("customers")
        elif unknown_contact:
            context_parts.append(self._format_unknown_visitor_hint(unknown_contact))

        # Histórico de pedidos do cliente
        if intent["needs_customer_history"] and self.customer_id:
            orders = db.get_customer_orders(self.customer_id)
            if orders:
                sources["tables"].append("orders")
                lines = ["\n## Historico de Pedidos\n"]
                seen = set()
                for o in orders:
                    if o["order_id"] not in seen:
                        seen.add(o["order_id"])
                        lines.append(
                            f"- Pedido #{o['order_id']} — {o['order_date']} — "
                            f"{o['order_status']} — R$ {o['total_brl']:.2f}"
                        )
                context_parts.append("\n".join(lines))

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

                rag_log = db.log_rag_query(
                    query_text=message,
                    query_embedding=metrics.get("query_embedding", []),
                    chunks_returned=sources["chunks"],
                    top_similarity=metrics.get("top_similarity"),
                    avg_similarity=metrics.get("avg_similarity"),
                    search_time_ms=metrics.get("search_time_ms", 0),
                    session_id=self.session_id,
                )
                sources["rag_log_id"] = rag_log.get("log_id")

        # Busca de produtos
        if intent["needs_product_search"] and intent["product_query"]:
            products = db.search_products(intent["product_query"])
            if products:
                sources["tables"].append("products")
                lines = [
                    "## Produtos Encontrados (dados reais do estoque)\n",
                    "Use EXATAMENTE as quantidades abaixo. Nao invente estoque.\n",
                ]
                for p in products:
                    stock_status = "disponivel" if p["stock_quantity"] > 0 else "ESGOTADO"
                    lines.append(
                        f"- **{p['product_name']}** ({p['category_name']}): "
                        f"R$ {p['price_brl']:.2f} | Estoque: {p['stock_quantity']} unidades ({stock_status})"
                    )
                context_parts.append("\n".join(lines))
            else:
                context_parts.append(
                    "## Produtos Encontrados\n\n"
                    f"Nenhum produto encontrado para a busca '{intent['product_query']}'. "
                    "Informe ao cliente que nao localizou esse item e peca o nome/modelo completo. "
                    "NAO invente estoque nem diga que esta esgotado sem dados."
                )

            promos = db.get_active_promotions()
            query_lower = intent["product_query"].lower()
            matching_promos = [
                p for p in promos
                if any(w in p["product_name"].lower() for w in query_lower.split() if len(w) > 2)
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

        # Pedido por ID
        if intent["needs_order_lookup"] and intent["order_id"]:
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

        # Rastreio por código
        if intent["needs_order_lookup"] and intent["tracking_code"]:
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

    # -------------------------------------------------------------------------
    # Montagem do prompt
    # -------------------------------------------------------------------------

    def _build_messages(self, user_message: str, context: str, history: list[dict]) -> list[dict]:
        """Monta lista de mensagens para a LLM."""
        messages = []

        system_content = self.system_prompt
        if context:
            system_content += (
                "\n\n---\n\n"
                "## DADOS JÁ CONSULTADOS DO SISTEMA\n\n"
                "As informações abaixo foram recuperadas automaticamente do banco de dados e da "
                "base de conhecimento. Apresente-as DIRETAMENTE ao cliente.\n\n"
                "REGRAS OBRIGATÓRIAS:\n"
                "- NÃO diga que vai verificar — a consulta já foi feita.\n"
                "- Para estoque/preço, use SOMENTE os números deste bloco.\n"
                "- NUNCA invente quantidade em estoque nem diga 'esgotado' sem constar abaixo.\n"
                "- Se o bloco disser que nenhum produto foi encontrado, peça o modelo completo.\n\n"
                + context
            )

        messages.append({"role": "system", "content": system_content})

        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        return messages

    # -------------------------------------------------------------------------
    # Método principal
    # -------------------------------------------------------------------------

    def chat(self, message: str) -> AgentResponse:
        """
        Processa mensagem do usuário e retorna resposta.

        Fluxo completo:
        1. Inicializa sessão e carrega prompt
        2. Salva mensagem do usuário
        3. Tenta identificar o cliente (email/telefone)
        4. Detecta intenção
        5. Reúne contexto (cliente + RAG + banco)
        6. Busca histórico da sessão
        7. Chama LLM
        8. Salva resposta com métricas
        9. Atualiza logs e contadores
        """
        self._initialize()

        # 1. Salva mensagem do usuário
        db.add_message(self.session_id, role="user", content=message)

        # 2. Tenta identificar o cliente
        contact = self._extract_contact(message)
        customer = self._identify_customer(message)

        # Se havia contato na mensagem mas não encontrou no banco
        unknown_contact = contact if (contact and not customer) else {}

        # 3. Detecta intenção
        intent = self._detect_intent(message)

        # 4. Reúne contexto
        context, sources = self._gather_context(message, intent, customer, unknown_contact)

        # 5. Histórico da sessão (últimas 10 trocas)
        history = db.get_session_messages(self.session_id)
        history = [m for m in history if m["content"] != message][-10:]

        # 6. Monta mensagens para a LLM
        messages = self._build_messages(message, context, history)

        # 7. Chama a LLM
        response_content, llm_metrics = llm.chat(messages)

        # 8. Salva resposta do agente
        rag_log_id = sources.pop("rag_log_id", None)

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

        # 9. Atualiza rag_query_log com message_id
        if rag_log_id:
            db.update_rag_log_message(rag_log_id, assistant_msg["message_id"])

        # 10. Incrementa uso do prompt
        db.increment_prompt_usage(self.prompt_id)

        return AgentResponse(
            content=response_content,
            message_id=assistant_msg["message_id"],
            model_used=llm_metrics["model_used"],
            tokens_input=llm_metrics["tokens_input"],
            tokens_output=llm_metrics["tokens_output"],
            response_time_ms=llm_metrics["response_time_ms"],
            sources_consulted=sources,
            rag_chunks_used=len(sources.get("chunks", [])),
            customer_identified=self.customer_id is not None,
        )

    def get_session_id(self) -> str:
        """Retorna o ID da sessão atual."""
        self._initialize()
        return self.session_id

    def get_customer(self) -> dict | None:
        """Retorna o cliente identificado, se houver."""
        return self.customer
