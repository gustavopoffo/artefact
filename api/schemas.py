"""Schemas Pydantic da API."""

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    channel: str = Field(default="web", description="Canal de origem (web, whatsapp, cli)")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: str
    status: str
    channel: str
    customer_id: int | None = None
    started_at: str | None = None
    ended_at: str | None = None


# ---------------------------------------------------------------------------
# Chat / Messages
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Mensagem do cliente")


class IdentifyRequest(BaseModel):
    phone: str = Field(..., min_length=8, description="Telefone/WhatsApp do cliente")


class IdentifyResponse(BaseModel):
    session_id: str
    identified: bool
    customer_id: int | None = None
    customer_name: str | None = None
    phone_normalized: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    content: str
    model_used: str
    tokens_input: int
    tokens_output: int
    response_time_ms: int
    rag_chunks_used: int
    customer_identified: bool
    sources_consulted: dict[str, Any] = Field(default_factory=dict)


class MessageItem(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: str | None = None
    rating: str | None = None
    response_time_ms: int | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    model_used: str | None = None


class MessageHistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageItem]


class RateMessageRequest(BaseModel):
    rating: str = Field(..., description="positive | negative | neutral")
    feedback: str | None = None


class RateMessageResponse(BaseModel):
    message_id: str
    rating: str
    rating_feedback: str | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str = "emporio-da-musica-agent"


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class AdminSessionItem(BaseModel):
    session_id: str
    started_at: str
    ended_at: str | None = None
    status: str
    channel: str
    customer_id: int | None = None
    customer_name: str | None = None
    message_count: int = 0
    last_message: str | None = None
    last_message_at: str | None = None


class DayCount(BaseModel):
    date: str
    count: int


class ChannelCount(BaseModel):
    channel: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class ResponseTimeTrend(BaseModel):
    date: str
    avg_ms: float


class AdminMetrics(BaseModel):
    total_sessions: int = 0
    active_sessions: int = 0
    total_messages: int = 0
    avg_response_time_ms: float = 0
    total_tokens_used: int = 0
    positive_ratings: int = 0
    negative_ratings: int = 0
    rag_queries: int = 0
    avg_rag_similarity: float = 0
    messages_by_day: list[DayCount] = []
    sessions_by_channel: list[ChannelCount] = []
    top_rag_categories: list[CategoryCount] = []
    response_time_trend: list[ResponseTimeTrend] = []


class PromotionItem(BaseModel):
    promotion_id: int
    product_id: int
    product_name: str
    product_status: str | None = None
    original_price: float
    discount_percent: float
    discounted_price: float
    description: str
    is_active: bool


class TogglePromotionRequest(BaseModel):
    is_active: bool


class AllowedModelItem(BaseModel):
    id: str
    label: str


class AdminSettingsResponse(BaseModel):
    llm_model: str
    allowed_models: list[AllowedModelItem]
    default_model: str = "gpt-4o"


class UpdateAdminSettingsRequest(BaseModel):
    llm_model: str = Field(..., description="ID do modelo OpenAI (ex: gpt-4o)")
