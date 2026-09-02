-- =============================================================================
-- SCHEMA: Sistema de Agente Conversacional
-- Objetivo: Controle de conversas entre clientes e IA para acompanhamento,
--           histórico e validação de acurácia das respostas
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TIPOS ENUMERADOS
-- -----------------------------------------------------------------------------

create type public.chat_role as enum ('user', 'assistant', 'system');
create type public.session_status as enum ('active', 'ended', 'abandoned');
create type public.message_rating as enum ('positive', 'negative', 'neutral');

-- -----------------------------------------------------------------------------
-- TABELA: chat_sessions
-- Sessões de conversa entre cliente e agente
-- Relacionamento: Pode pertencer a um cliente (N:1 com customers, nullable)
-- Relacionamento: Possui muitas mensagens (1:N com chat_messages)
-- -----------------------------------------------------------------------------

create table public.chat_sessions (
  session_id uuid primary key default gen_random_uuid(),
  customer_id integer,
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  status public.session_status not null default 'active',
  channel text not null default 'web',
  metadata jsonb default '{}',
  
  constraint fk_sessions_customer 
    foreign key (customer_id) 
    references public.customers (customer_id) 
    on update cascade 
    on delete set null,
    
  constraint chk_ended_after_started 
    check (ended_at is null or ended_at >= started_at)
);

comment on table public.chat_sessions is 'Sessões de conversa com o agente. Uma sessão agrupa todas as mensagens de uma interação contínua';
comment on column public.chat_sessions.session_id is 'Identificador único da sessão (UUID)';
comment on column public.chat_sessions.customer_id is 'FK para customers. Null se cliente não identificado/logado';
comment on column public.chat_sessions.started_at is 'Timestamp de início da sessão';
comment on column public.chat_sessions.ended_at is 'Timestamp de encerramento da sessão';
comment on column public.chat_sessions.status is 'Status: active (em andamento), ended (encerrada pelo cliente), abandoned (timeout)';
comment on column public.chat_sessions.channel is 'Canal de origem: web, whatsapp, telegram, etc.';
comment on column public.chat_sessions.metadata is 'Metadados extras: user_agent, ip, device, etc.';

create index idx_sessions_customer_id on public.chat_sessions (customer_id);
create index idx_sessions_status on public.chat_sessions (status);
create index idx_sessions_started_at on public.chat_sessions (started_at desc);

-- -----------------------------------------------------------------------------
-- TABELA: chat_messages
-- Mensagens individuais em cada sessão de conversa
-- Relacionamento: Pertence a uma sessão (N:1 com chat_sessions)
-- Armazena tanto mensagens do cliente (user) quanto respostas da IA (assistant)
-- -----------------------------------------------------------------------------

create table public.chat_messages (
  message_id uuid primary key default gen_random_uuid(),
  session_id uuid not null,
  role public.chat_role not null,
  content text not null,
  created_at timestamptz not null default now(),
  
  -- Métricas do agente (preenchidas apenas para role = 'assistant')
  model_used text,
  tokens_input integer,
  tokens_output integer,
  response_time_ms integer,
  
  -- Fontes consultadas pela IA
  sources_consulted jsonb default '[]',
  
  -- Controle de qualidade
  rating public.message_rating,
  rating_feedback text,
  rated_at timestamptz,
  
  constraint fk_messages_session 
    foreign key (session_id) 
    references public.chat_sessions (session_id) 
    on update cascade 
    on delete cascade,
    
  constraint chk_tokens_positive 
    check (tokens_input is null or tokens_input >= 0),
    
  constraint chk_response_time_positive 
    check (response_time_ms is null or response_time_ms >= 0)
);

comment on table public.chat_messages is 'Mensagens individuais de cada conversa. Armazena falas do cliente (user) e respostas da IA (assistant)';
comment on column public.chat_messages.message_id is 'Identificador único da mensagem (UUID)';
comment on column public.chat_messages.session_id is 'FK para chat_sessions. Sessão à qual a mensagem pertence';
comment on column public.chat_messages.role is 'Papel: user (cliente), assistant (IA), system (instruções internas)';
comment on column public.chat_messages.content is 'Conteúdo textual da mensagem';
comment on column public.chat_messages.created_at is 'Timestamp exato de quando a mensagem foi criada';
comment on column public.chat_messages.model_used is 'Modelo de IA usado (ex: gpt-4, claude-3). Apenas para role=assistant';
comment on column public.chat_messages.tokens_input is 'Tokens de entrada consumidos. Apenas para role=assistant';
comment on column public.chat_messages.tokens_output is 'Tokens de saída gerados. Apenas para role=assistant';
comment on column public.chat_messages.response_time_ms is 'Tempo de resposta em milissegundos. Apenas para role=assistant';
comment on column public.chat_messages.sources_consulted is 'JSON com fontes consultadas: tabelas do banco, documentos, políticas da loja';
comment on column public.chat_messages.rating is 'Avaliação da resposta: positive (útil), negative (incorreta/ruim), neutral';
comment on column public.chat_messages.rating_feedback is 'Feedback textual do avaliador sobre a resposta';
comment on column public.chat_messages.rated_at is 'Timestamp de quando a avaliação foi feita';

create index idx_messages_session_id on public.chat_messages (session_id);
create index idx_messages_created_at on public.chat_messages (created_at desc);
create index idx_messages_role on public.chat_messages (role);
create index idx_messages_rating on public.chat_messages (rating) where rating is not null;
create index idx_messages_model on public.chat_messages (model_used) where model_used is not null;

-- -----------------------------------------------------------------------------
-- TABELA: knowledge_sources
-- Fontes de conhecimento disponíveis para o agente (documentos, políticas, etc.)
-- -----------------------------------------------------------------------------

create table public.knowledge_sources (
  source_id uuid primary key default gen_random_uuid(),
  name text not null unique,
  source_type text not null,
  content text,
  file_path text,
  embedding_status text default 'pending',
  last_updated_at timestamptz not null default now(),
  metadata jsonb default '{}'
);

comment on table public.knowledge_sources is 'Fontes de conhecimento do agente: políticas da loja, FAQs, documentos internos';
comment on column public.knowledge_sources.source_id is 'Identificador único da fonte (UUID)';
comment on column public.knowledge_sources.name is 'Nome identificador da fonte (ex: politicas_da_loja)';
comment on column public.knowledge_sources.source_type is 'Tipo: document, policy, faq, database_schema';
comment on column public.knowledge_sources.content is 'Conteúdo textual (para documentos pequenos)';
comment on column public.knowledge_sources.file_path is 'Caminho do arquivo original';
comment on column public.knowledge_sources.embedding_status is 'Status do embedding: pending, processing, completed, failed';
comment on column public.knowledge_sources.last_updated_at is 'Última atualização do conteúdo';
comment on column public.knowledge_sources.metadata is 'Metadados extras: versão, autor, tags';

-- =============================================================================
-- VIEWS: Consultas para acompanhamento e métricas do agente
-- =============================================================================

-- -----------------------------------------------------------------------------
-- VIEW: v_chat_sessions_summary
-- Resumo de sessões de chat com métricas
-- -----------------------------------------------------------------------------

create view public.v_chat_sessions_summary as
select 
  s.session_id,
  s.customer_id,
  c.name as customer_name,
  c.email as customer_email,
  s.started_at,
  s.ended_at,
  s.status,
  s.channel,
  extract(epoch from (coalesce(s.ended_at, now()) - s.started_at)) / 60 as duration_minutes,
  count(m.message_id) as total_messages,
  count(case when m.role = 'user' then 1 end) as user_messages,
  count(case when m.role = 'assistant' then 1 end) as assistant_messages,
  avg(case when m.role = 'assistant' then m.response_time_ms end) as avg_response_time_ms,
  sum(case when m.role = 'assistant' then m.tokens_input + m.tokens_output end) as total_tokens_used
from public.chat_sessions s
left join public.customers c on s.customer_id = c.customer_id
left join public.chat_messages m on s.session_id = m.session_id
group by s.session_id, s.customer_id, c.name, c.email, s.started_at, s.ended_at, s.status, s.channel;

comment on view public.v_chat_sessions_summary is 'Resumo de sessões de chat com contagem de mensagens, duração e tokens consumidos';

-- -----------------------------------------------------------------------------
-- VIEW: v_agent_accuracy_metrics
-- Métricas de acurácia do agente baseadas em avaliações
-- -----------------------------------------------------------------------------

create view public.v_agent_accuracy_metrics as
select 
  date_trunc('day', m.created_at) as date,
  m.model_used,
  count(*) as total_responses,
  count(case when m.rating = 'positive' then 1 end) as positive_ratings,
  count(case when m.rating = 'negative' then 1 end) as negative_ratings,
  count(case when m.rating = 'neutral' then 1 end) as neutral_ratings,
  count(case when m.rating is null then 1 end) as unrated,
  round(
    100.0 * count(case when m.rating = 'positive' then 1 end) / 
    nullif(count(case when m.rating is not null then 1 end), 0), 
    2
  ) as accuracy_percent,
  avg(m.response_time_ms) as avg_response_time_ms,
  sum(m.tokens_input + m.tokens_output) as total_tokens
from public.chat_messages m
where m.role = 'assistant'
group by date_trunc('day', m.created_at), m.model_used;

comment on view public.v_agent_accuracy_metrics is 'Métricas diárias de acurácia do agente. Accuracy = positivos / total avaliados';

-- -----------------------------------------------------------------------------
-- VIEW: v_chat_conversation_history
-- Histórico de conversa formatado para exibição no frontend
-- -----------------------------------------------------------------------------

create view public.v_chat_conversation_history as
select 
  m.message_id,
  m.session_id,
  s.customer_id,
  c.name as customer_name,
  m.role,
  m.content,
  m.created_at,
  m.model_used,
  m.response_time_ms,
  m.sources_consulted,
  m.rating,
  m.rating_feedback
from public.chat_messages m
join public.chat_sessions s on m.session_id = s.session_id
left join public.customers c on s.customer_id = c.customer_id
order by m.session_id, m.created_at;

comment on view public.v_chat_conversation_history is 'Histórico completo de conversas ordenado por sessão e timestamp. Use para exibir no frontend';

-- -----------------------------------------------------------------------------
-- VIEW: v_customer_chat_history
-- Histórico de chats por cliente (para consulta do agente)
-- -----------------------------------------------------------------------------

create view public.v_customer_chat_history as
select 
  c.customer_id,
  c.name as customer_name,
  c.email,
  c.city,
  count(distinct s.session_id) as total_sessions,
  count(m.message_id) as total_messages,
  min(s.started_at) as first_interaction,
  max(s.started_at) as last_interaction,
  array_agg(distinct s.channel) as channels_used
from public.customers c
left join public.chat_sessions s on c.customer_id = s.customer_id
left join public.chat_messages m on s.session_id = m.session_id
group by c.customer_id, c.name, c.email, c.city;

comment on view public.v_customer_chat_history is 'Histórico de interações por cliente. Útil para o agente personalizar atendimento';

-- -----------------------------------------------------------------------------
-- VIEW: v_low_rated_responses
-- Respostas com avaliação negativa para revisão e melhoria
-- -----------------------------------------------------------------------------

create view public.v_low_rated_responses as
select 
  m.message_id,
  m.session_id,
  m.content as assistant_response,
  m.created_at,
  m.model_used,
  m.sources_consulted,
  m.rating_feedback,
  lag(m2.content) over (partition by m.session_id order by m2.created_at) as user_question,
  c.name as customer_name
from public.chat_messages m
join public.chat_sessions s on m.session_id = s.session_id
left join public.customers c on s.customer_id = c.customer_id
left join public.chat_messages m2 on m.session_id = m2.session_id and m2.role = 'user'
where m.role = 'assistant' and m.rating = 'negative'
order by m.created_at desc;

comment on view public.v_low_rated_responses is 'Respostas avaliadas negativamente. Use para identificar pontos de melhoria do agente';
