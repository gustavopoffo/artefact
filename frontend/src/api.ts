const API_BASE = 'http://localhost:8000';

export interface Session {
  session_id: string;
  status: string;
  channel: string;
  customer_id: number | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string | null;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  content: string;
  model_used: string;
  tokens_input: number;
  tokens_output: number;
  response_time_ms: number;
  rag_chunks_used: number;
  customer_identified: boolean;
  sources_consulted: Record<string, unknown>;
}

export interface IdentifyResponse {
  session_id: string;
  identified: boolean;
  customer_id: number | null;
  customer_name: string | null;
  phone_normalized: string | null;
  message: string;
}

export interface SessionSummary {
  session_id: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  channel: string;
  customer_id: number | null;
  customer_name?: string;
  message_count?: number;
  last_message?: string;
}

// Health check
export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

// Sessions
export async function createSession(channel: string = 'web'): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel }),
  });
  if (!res.ok) throw new Error('Falha ao criar sessão');
  return res.json();
}

export async function getSession(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error('Sessão não encontrada');
  return res.json();
}

export async function endSession(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/end`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Falha ao encerrar sessão');
  return res.json();
}

// Messages
export async function sendMessage(sessionId: string, message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'Falha ao enviar mensagem');
  }
  return res.json();
}

export async function identifyByPhone(sessionId: string, phone: string): Promise<IdentifyResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/identify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'Falha ao identificar cliente');
  }
  return res.json();
}

export async function getMessages(sessionId: string, limit: number = 50): Promise<{ session_id: string; messages: Message[] }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages?limit=${limit}`);
  if (!res.ok) throw new Error('Falha ao buscar mensagens');
  return res.json();
}

// Admin: List all sessions (via Supabase direct - placeholder for now)
export async function listSessions(): Promise<SessionSummary[]> {
  // This would typically call a dedicated admin endpoint
  // For now, we'll return empty and implement later
  const res = await fetch(`${API_BASE}/admin/sessions`);
  if (!res.ok) return [];
  return res.json();
}

// Admin: Get metrics (placeholder)
export async function getMetrics(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/admin/metrics`);
  if (!res.ok) return {};
  return res.json();
}

export interface Promotion {
  promotion_id: number;
  product_id: number;
  product_name: string;
  product_status: string | null;
  original_price: number;
  discount_percent: number;
  discounted_price: number;
  description: string;
  is_active: boolean;
}

export async function listPromotions(): Promise<Promotion[]> {
  const res = await fetch(`${API_BASE}/admin/promotions`);
  if (!res.ok) throw new Error('Falha ao listar promoções');
  return res.json();
}

export async function togglePromotion(promotionId: number, isActive: boolean): Promise<Promotion> {
  const res = await fetch(`${API_BASE}/admin/promotions/${promotionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_active: isActive }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || 'Falha ao atualizar promoção');
  }
  return res.json();
}
