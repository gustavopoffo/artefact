"""
Agente de chat — orquestra todo o fluxo de conversa.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .database import db
from .rag import rag
from .llm import llm

STORE_TZ = ZoneInfo("America/Campo_Grande")
WEEKDAY_NAMES_PT = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def _normalize(text: str) -> str:
    """Remove acentos e coloca em minúsculas para comparações robustas."""
    return unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode("ascii")


def _clean_client_text(text: str) -> str:
    """Remove markdown de negrito/itálico que aparece literal no WhatsApp."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)
    return text


def _store_hours_for_weekday(weekday: int) -> tuple[time, time] | None:
    """Retorna (abertura, fechamento) ou None se fechado. weekday: seg=0 … dom=6."""
    if weekday <= 4:  # seg–sex
        return time(9, 0), time(18, 0)
    if weekday == 5:  # sábado
        return time(9, 0), time(13, 0)
    return None


def _next_opening(now: datetime) -> datetime:
    """Próximo horário de abertura a partir de now (timezone da loja)."""
    candidate = now
    for _ in range(8):
        hours = _store_hours_for_weekday(candidate.weekday())
        if hours:
            open_at, _ = hours
            opening = candidate.replace(
                hour=open_at.hour, minute=open_at.minute, second=0, microsecond=0
            )
            if candidate.date() > now.date() or opening > now:
                return opening
        candidate = (candidate + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    return now + timedelta(days=1)


def format_attendance_status(now: datetime | None = None) -> str:
    """
    Bloco de contexto com horário local e se a loja está aberta.
    O prompt usa isso para avisar fora do expediente.
    """
    now = now or datetime.now(STORE_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=STORE_TZ)
    else:
        now = now.astimezone(STORE_TZ)

    hours = _store_hours_for_weekday(now.weekday())
    weekday = WEEKDAY_NAMES_PT[now.weekday()]
    clock = now.strftime("%H:%M")
    date_str = now.strftime("%d/%m/%Y")

    if hours:
        open_at, close_at = hours
        is_open = open_at <= now.time() < close_at
    else:
        open_at = close_at = None
        is_open = False

    lines = [
        "## STATUS DO ATENDIMENTO\n",
        f"- **Agora:** {weekday}, {date_str}, {clock} (Campo Grande, MS)",
        "- **Expediente:** Seg-Sex 09:00-18:00 | Sab 09:00-13:00 | Dom/feriados fechado",
    ]

    if is_open:
        lines.append(
            f"- **Status:** DENTRO DO EXPEDIENTE (abre {open_at.strftime('%H:%M')}, "
            f"fecha {close_at.strftime('%H:%M')})"
        )
        lines.append("- Não é necessário avisar horário de retorno.")
    else:
        nxt = _next_opening(now)
        next_label = WEEKDAY_NAMES_PT[nxt.weekday()]
        lines.append("- **Status:** FORA DO EXPEDIENTE")
        lines.append(
            f"- **Retorno:** {next_label} às {nxt.strftime('%H:%M')}"
        )
        lines.append(
            "- Na primeira resposta da sessão, avise que estão fora do horário "
            "e informe o retorno. Continue ajudando com informações disponíveis."
        )

    return "\n".join(lines)


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
            normalized = db.normalize_phone(raw)
            if normalized:
                contact["phone"] = normalized
            else:
                contact["phone"] = phone_match.group(0)

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
            "\nUse o nome do cliente na saudacao e ocasionalmente depois. "
            "Se tiver pedidos, pode referenciar o historico se relevante. "
            "Nao peca telefone/email de novo — o cadastro ja foi localizado."
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

        # Horário local da loja (sempre — o prompt usa para fora do expediente)
        context_parts.append(format_attendance_status())

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
                    query_embedding=None,
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
            active_promos = {
                p["product_id"]: p for p in db.get_active_promotions()
            }
            if products:
                sources["tables"].append("products")
                lines = [
                    "## Produtos Encontrados (dados reais do estoque)\n",
                    "Use EXATAMENTE as quantidades e precos abaixo. Nao invente estoque.\n",
                    "Se houver preco promocional, apresente de/por com o percentual.\n",
                ]
                for p in products:
                    stock_status = "disponivel" if p["stock_quantity"] > 0 else "ESGOTADO"
                    promo = active_promos.get(p["product_id"])
                    if promo:
                        sources["tables"].append("promotions")
                        lines.append(
                            f"- {p['product_name']} ({p['category_name']}): "
                            f"de R$ {promo['original_price']:.2f} por R$ {promo['discounted_price']:.2f} "
                            f"({promo['discount_percent']:.0f}% OFF — {promo['promotion_name']}) | "
                            f"Estoque: {p['stock_quantity']} unidades ({stock_status})"
                        )
                    else:
                        lines.append(
                            f"- {p['product_name']} ({p['category_name']}): "
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

            # Promoções ativas gerais (mesmo sem match no nome da busca)
            promos = list(active_promos.values())
            query_lower = intent["product_query"].lower()
            matching_promos = [
                p for p in promos
                if any(w in p["product_name"].lower() for w in query_lower.split() if len(w) > 2)
            ]
            if matching_promos and "promotions" not in sources["tables"]:
                sources["tables"].append("promotions")
            if matching_promos:
                # Já embutidas na lista de produtos acima; reforço só se produto não veio na busca
                listed_ids = {p["product_id"] for p in products} if products else set()
                extra = [p for p in matching_promos if p["product_id"] not in listed_ids]
                if extra:
                    lines = ["\n## Outras Promocoes Relacionadas\n"]
                    for p in extra:
                        lines.append(
                            f"- {p['product_name']}: de R$ {p['original_price']:.2f} "
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
                    f"- Cliente: {o['customer_name']}",
                    f"- Data: {o['order_date']}",
                    f"- Status: {o['order_status']}",
                    f"- Total: R$ {o['total_brl']:.2f}",
                    f"- Pagamento: {o['payment_method']}",
                ]
                if o.get("tracking_code"):
                    lines.append(f"- Rastreio: {o['tracking_code']}")
                if o.get("estimated_delivery"):
                    lines.append(f"- Previsao de entrega: {o['estimated_delivery']}")
                lines.append("\nItens:")
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
        """
        Monta mensagens para a LLM.
        System prompt fica estático (melhor cache/prefixo na OpenAI);
        dados dinâmicos vão em mensagem system separada.
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        if context:
            messages.append({
                "role": "system",
                "content": (
                    "## DADOS JÁ CONSULTADOS DO SISTEMA\n\n"
                    "Informações recuperadas automaticamente. Apresente DIRETAMENTE ao cliente.\n"
                    "- NÃO diga que vai verificar — a consulta já foi feita.\n"
                    "- Estoque/preço: use SOMENTE os números deste bloco.\n"
                    "- NUNCA invente estoque nem diga esgotado sem constar abaixo.\n"
                    "- Se nenhum produto foi encontrado, peça o modelo completo.\n"
                    "- Resposta em texto limpo: SEM markdown, SEM asteriscos (**nome**), "
                    "SEM negrito. Escreva o nome do produto em texto normal.\n"
                    "- Emoji só se necessário; evite em listas de produto.\n\n"
                    + context
                ),
            })

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

        # 5. Histórico da sessão (últimas 6 mensagens — menos tokens)
        history = db.get_session_messages(self.session_id)
        history = [m for m in history if m["content"] != message][-6:]

        # 6. Monta mensagens para a LLM
        messages = self._build_messages(message, context, history)

        # 7. Chama a LLM (modelo configurável no admin)
        from .runtime_settings import get_llm_model

        response_content, llm_metrics = llm.chat(messages, model=get_llm_model())
        response_content = _clean_client_text(response_content)

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
