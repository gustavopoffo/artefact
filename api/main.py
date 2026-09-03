"""
API REST do Agente Conversacional — Empório da Música.

Uso:
    uvicorn api.main:app --reload --port 8000

Docs interativas:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent import Agent
from agent.database import db

from .schemas import (
    AdminMetrics,
    AdminSessionItem,
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    HealthResponse,
    IdentifyRequest,
    IdentifyResponse,
    MessageHistoryResponse,
    MessageItem,
    PromotionItem,
    RateMessageRequest,
    RateMessageResponse,
    SessionResponse,
    TogglePromotionRequest,
)

app = FastAPI(
    title="Empório da Música — Agent API",
    description=(
        "API do agente conversacional de atendimento. "
        "Cria sessões, envia mensagens e consulta histórico."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Verifica se a API está no ar."""
    return HealthResponse(status="ok")


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@app.post("/sessions", response_model=SessionResponse, tags=["sessions"])
def create_session(body: CreateSessionRequest) -> SessionResponse:
    """Cria uma nova sessão de chat."""
    session = db.create_session(channel=body.channel, metadata=body.metadata)
    return SessionResponse(
        session_id=session["session_id"],
        status=session.get("status", "active"),
        channel=session.get("channel", body.channel),
        customer_id=session.get("customer_id"),
        started_at=session.get("started_at"),
        ended_at=session.get("ended_at"),
    )


@app.get("/sessions/{session_id}", response_model=SessionResponse, tags=["sessions"])
def get_session(session_id: str) -> SessionResponse:
    """Retorna dados de uma sessão."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    return SessionResponse(
        session_id=session["session_id"],
        status=session.get("status", "active"),
        channel=session.get("channel", "web"),
        customer_id=session.get("customer_id"),
        started_at=session.get("started_at"),
        ended_at=session.get("ended_at"),
    )


@app.post("/sessions/{session_id}/end", response_model=SessionResponse, tags=["sessions"])
def end_session(session_id: str) -> SessionResponse:
    """Encerra uma sessão de chat."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    updated = db.end_session(session_id)
    return SessionResponse(
        session_id=updated["session_id"],
        status=updated.get("status", "ended"),
        channel=updated.get("channel", session.get("channel", "web")),
        customer_id=updated.get("customer_id"),
        started_at=updated.get("started_at"),
        ended_at=updated.get("ended_at"),
    )


@app.post(
    "/sessions/{session_id}/identify",
    response_model=IdentifyResponse,
    tags=["sessions"],
)
def identify_customer(session_id: str, body: IdentifyRequest) -> IdentifyResponse:
    """
    Identifica o cliente pelo telefone e vincula à sessão.
    Usado pelo campo opcional do header no chat web.
    """
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session.get("status") == "ended":
        raise HTTPException(status_code=400, detail="Sessao ja encerrada")

    normalized = db.normalize_phone(body.phone)
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Telefone invalido. Use DDD + numero (ex: 67 99812-3456).",
        )

    customer = db.find_customer_by_phone(normalized)
    if not customer:
        return IdentifyResponse(
            session_id=session_id,
            identified=False,
            phone_normalized=normalized,
            message="Nao encontramos esse numero no cadastro. Pode continuar normalmente.",
        )

    db.link_customer_to_session(session_id, customer["customer_id"])
    first_name = (customer.get("name") or "").split()[0] or customer.get("name")

    return IdentifyResponse(
        session_id=session_id,
        identified=True,
        customer_id=customer["customer_id"],
        customer_name=customer.get("name"),
        phone_normalized=normalized,
        message=f"Ola, {first_name}! Cadastro localizado.",
    )


# ---------------------------------------------------------------------------
# Messages / Chat
# ---------------------------------------------------------------------------

@app.post(
    "/sessions/{session_id}/messages",
    response_model=ChatResponse,
    tags=["chat"],
)
def send_message(session_id: str, body: ChatRequest) -> ChatResponse:
    """
    Envia uma mensagem do cliente e retorna a resposta do agente.

    O agente consulta RAG, banco de produtos/pedidos e gera a resposta via LLM.
    Toda a interação é persistida em chat_messages com métricas.
    """
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    if session.get("status") == "ended":
        raise HTTPException(status_code=400, detail="Sessao ja encerrada")

    try:
        agent = Agent(session_id=session_id, channel=session.get("channel", "web"))
        response = agent.chat(body.message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar mensagem: {e}") from e

    return ChatResponse(
        session_id=session_id,
        message_id=response.message_id,
        content=response.content,
        model_used=response.model_used,
        tokens_input=response.tokens_input,
        tokens_output=response.tokens_output,
        response_time_ms=response.response_time_ms,
        rag_chunks_used=response.rag_chunks_used,
        customer_identified=response.customer_identified,
        sources_consulted=response.sources_consulted,
    )


@app.get(
    "/sessions/{session_id}/messages",
    response_model=MessageHistoryResponse,
    tags=["chat"],
)
def get_messages(session_id: str, limit: int = 50) -> MessageHistoryResponse:
    """Retorna o histórico de mensagens da sessão."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    rows = db.get_session_messages(session_id, limit=limit)
    messages = [
        MessageItem(
            message_id=m["message_id"],
            role=m["role"],
            content=m["content"],
            created_at=m.get("created_at"),
            rating=m.get("rating"),
            response_time_ms=m.get("response_time_ms"),
            tokens_input=m.get("tokens_input"),
            tokens_output=m.get("tokens_output"),
            model_used=m.get("model_used"),
        )
        for m in rows
    ]

    return MessageHistoryResponse(session_id=session_id, messages=messages)


@app.patch(
    "/admin/messages/{message_id}/rating",
    response_model=RateMessageResponse,
    tags=["admin"],
)
def rate_message(message_id: str, body: RateMessageRequest) -> RateMessageResponse:
    """Avalia uma resposta do agente. Alimenta a acurácia do dashboard."""
    if body.rating not in ("positive", "negative", "neutral"):
        raise HTTPException(
            status_code=400,
            detail="rating deve ser positive, negative ou neutral",
        )

    try:
        updated = db.rate_message(message_id, body.rating, body.feedback)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if not updated:
        raise HTTPException(status_code=404, detail="Mensagem nao encontrada")

    return RateMessageResponse(
        message_id=updated.get("message_id", message_id),
        rating=updated.get("rating", body.rating),
        rating_feedback=updated.get("rating_feedback"),
    )


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.get("/admin/sessions", response_model=list[AdminSessionItem], tags=["admin"])
def list_sessions(limit: int = 100) -> list[AdminSessionItem]:
    """Lista todas as sessões com resumo (para painel admin)."""
    sessions = db.list_sessions_with_summary(limit=limit)
    return [
        AdminSessionItem(
            session_id=s["session_id"],
            started_at=s["started_at"],
            ended_at=s.get("ended_at"),
            status=s["status"],
            channel=s["channel"],
            customer_id=s.get("customer_id"),
            customer_name=s.get("customer_name"),
            message_count=s.get("message_count", 0),
            last_message=s.get("last_message"),
            last_message_at=s.get("last_message_at"),
        )
        for s in sessions
    ]


@app.get("/admin/metrics", response_model=AdminMetrics, tags=["admin"])
def get_metrics() -> AdminMetrics:
    """Retorna métricas agregadas para o dashboard."""
    metrics = db.get_admin_metrics()
    return AdminMetrics(**metrics)


@app.get("/admin/promotions", response_model=list[PromotionItem], tags=["admin"])
def list_promotions() -> list[PromotionItem]:
    """Lista promoções com preço original e preço com desconto."""
    rows = db.list_promotions()
    return [PromotionItem(**row) for row in rows]


@app.patch(
    "/admin/promotions/{promotion_id}",
    response_model=PromotionItem,
    tags=["admin"],
)
def toggle_promotion(promotion_id: int, body: TogglePromotionRequest) -> PromotionItem:
    """Ativa ou desativa uma promoção (is_active). O agente passa a usar o preço correspondente."""
    updated = db.set_promotion_active(promotion_id, body.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="Promocao nao encontrada")
    return PromotionItem(**updated)
