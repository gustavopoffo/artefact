-- =============================================================================
-- SCHEMA: RAG e Versionamento de Prompts
-- Objetivo: Estrutura para controle de prompts do agente e chunks de conhecimento
-- =============================================================================

-- Habilitar extensão pgvector para embeddings
create extension if not exists vector;

-- -----------------------------------------------------------------------------
-- TABELA: agent_prompts
-- Versionamento de prompts do agente para controle e comparação de performance
-- -----------------------------------------------------------------------------

create table public.agent_prompts (
  prompt_id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  content text not null,
  version text not null,
  is_active boolean not null default false,
  tokens_estimated integer,
  
  -- Métricas de uso (atualizadas pelo sistema)
  times_used integer default 0,
  avg_accuracy numeric(5,2),
  
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  
  constraint uq_prompt_name_version unique (name, version)
);

comment on table public.agent_prompts is 'Prompts versionados do agente. Apenas um prompt por nome pode estar ativo (is_active=true)';
comment on column public.agent_prompts.name is 'Identificador do prompt (ex: system_prompt, greeting)';
comment on column public.agent_prompts.description is 'Descrição das mudanças nesta versão';
comment on column public.agent_prompts.content is 'Conteúdo completo do prompt';
comment on column public.agent_prompts.version is 'Versão semântica (ex: 1.0.0, 1.1.0)';
comment on column public.agent_prompts.is_active is 'Se true, este é o prompt ativo para uso. Apenas um por nome';
comment on column public.agent_prompts.tokens_estimated is 'Estimativa de tokens do prompt (para controle de custo)';
comment on column public.agent_prompts.times_used is 'Contador de vezes que este prompt foi usado';
comment on column public.agent_prompts.avg_accuracy is 'Média de acurácia das respostas usando este prompt';

create index idx_prompts_active on public.agent_prompts (name, is_active) where is_active = true;
create index idx_prompts_name on public.agent_prompts (name);

-- Trigger para garantir apenas um prompt ativo por nome
create or replace function public.ensure_single_active_prompt()
returns trigger as $$
begin
  if NEW.is_active = true then
    update public.agent_prompts 
    set is_active = false, updated_at = now()
    where name = NEW.name 
      and prompt_id != NEW.prompt_id 
      and is_active = true;
  end if;
  return NEW;
end;
$$ language plpgsql;

create trigger trg_single_active_prompt
  before insert or update on public.agent_prompts
  for each row execute function public.ensure_single_active_prompt();

-- -----------------------------------------------------------------------------
-- TABELA: rag_chunks
-- Chunks de conhecimento com embeddings para busca semântica
-- -----------------------------------------------------------------------------

create table public.rag_chunks (
  chunk_id uuid primary key default gen_random_uuid(),
  
  -- Conteúdo
  content text not null,
  content_hash text not null,
  
  -- Embedding (1536 dimensões = OpenAI text-embedding-3-small)
  embedding vector(1536),
  
  -- Metadados de origem
  source_document text not null,
  source_section text not null,
  source_subsection text,
  section_number text,
  
  -- Metadados de chunking
  chunk_index integer not null,
  total_chunks_in_section integer,
  tokens_count integer,
  
  -- Categorização para filtro
  category text not null,
  keywords text[],
  
  -- Controle
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  
  constraint uq_chunk_hash unique (content_hash)
);

comment on table public.rag_chunks is 'Chunks de conhecimento para RAG. Cada chunk representa uma unidade semântica de informação';
comment on column public.rag_chunks.content is 'Conteúdo textual do chunk';
comment on column public.rag_chunks.content_hash is 'SHA256 do conteúdo para evitar duplicatas';
comment on column public.rag_chunks.embedding is 'Vetor de embedding (1536 dims) para busca por similaridade';
comment on column public.rag_chunks.source_document is 'Documento de origem (ex: politicas_da_loja.pdf)';
comment on column public.rag_chunks.source_section is 'Seção principal (ex: Formas de Pagamento)';
comment on column public.rag_chunks.source_subsection is 'Subseção se houver (ex: Regras de Parcelamento)';
comment on column public.rag_chunks.section_number is 'Número da seção no documento (ex: 3.1)';
comment on column public.rag_chunks.chunk_index is 'Índice do chunk dentro da seção (0-based)';
comment on column public.rag_chunks.total_chunks_in_section is 'Total de chunks nesta seção';
comment on column public.rag_chunks.tokens_count is 'Contagem de tokens do chunk';
comment on column public.rag_chunks.category is 'Categoria para filtro (pagamento, troca, frete, promocao, garantia, lgpd)';
comment on column public.rag_chunks.keywords is 'Palavras-chave para busca auxiliar';
comment on column public.rag_chunks.is_active is 'Se false, chunk foi desativado (não deletado para histórico)';

-- Índice para busca por similaridade de cosseno (IVFFlat)
create index idx_chunks_embedding on public.rag_chunks 
  using ivfflat (embedding vector_cosine_ops) 
  with (lists = 50);

create index idx_chunks_category on public.rag_chunks (category) where is_active = true;
create index idx_chunks_section on public.rag_chunks (source_section) where is_active = true;
create index idx_chunks_active on public.rag_chunks (is_active);

-- -----------------------------------------------------------------------------
-- FUNÇÃO: match_chunks
-- Busca chunks similares a um embedding de query
-- -----------------------------------------------------------------------------

create or replace function public.match_chunks(
  query_embedding vector(1536),
  match_count integer default 3,
  similarity_threshold float default 0.5,
  filter_category text default null
)
returns table (
  chunk_id uuid,
  content text,
  source_section text,
  source_subsection text,
  section_number text,
  category text,
  keywords text[],
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    rc.chunk_id,
    rc.content,
    rc.source_section,
    rc.source_subsection,
    rc.section_number,
    rc.category,
    rc.keywords,
    1 - (rc.embedding <=> query_embedding) as similarity
  from public.rag_chunks rc
  where rc.is_active = true
    and (filter_category is null or rc.category = filter_category)
    and 1 - (rc.embedding <=> query_embedding) > similarity_threshold
  order by rc.embedding <=> query_embedding
  limit match_count;
end;
$$;

comment on function public.match_chunks is 'Busca chunks similares ao embedding da query. Retorna ordenado por similaridade decrescente';

-- -----------------------------------------------------------------------------
-- TABELA: rag_query_log
-- Log de queries RAG para análise de performance e melhoria
-- -----------------------------------------------------------------------------

create table public.rag_query_log (
  log_id uuid primary key default gen_random_uuid(),
  
  -- Query
  query_text text not null,
  query_embedding vector(1536),
  
  -- Resultados
  chunks_returned uuid[],
  chunks_count integer,
  top_similarity float,
  avg_similarity float,
  
  -- Contexto
  session_id uuid references public.chat_sessions(session_id) on delete set null,
  message_id uuid references public.chat_messages(message_id) on delete set null,
  
  -- Performance
  search_time_ms integer,
  
  -- Feedback (preenchido após avaliação)
  was_relevant boolean,
  feedback_notes text,
  
  created_at timestamptz not null default now()
);

comment on table public.rag_query_log is 'Log de todas as buscas RAG para análise e melhoria contínua';
comment on column public.rag_query_log.query_text is 'Texto original da pergunta do usuário';
comment on column public.rag_query_log.chunks_returned is 'Array de chunk_ids retornados';
comment on column public.rag_query_log.top_similarity is 'Maior similaridade encontrada';
comment on column public.rag_query_log.was_relevant is 'Se os chunks retornados eram relevantes (feedback manual)';

create index idx_rag_log_session on public.rag_query_log (session_id);
create index idx_rag_log_created on public.rag_query_log (created_at desc);
create index idx_rag_log_relevance on public.rag_query_log (was_relevant) where was_relevant is not null;

-- -----------------------------------------------------------------------------
-- VIEW: v_rag_performance
-- Métricas de performance do RAG
-- -----------------------------------------------------------------------------

create view public.v_rag_performance as
select
  date_trunc('day', created_at) as date,
  count(*) as total_queries,
  avg(top_similarity) as avg_top_similarity,
  avg(avg_similarity) as avg_avg_similarity,
  avg(chunks_count) as avg_chunks_returned,
  avg(search_time_ms) as avg_search_time_ms,
  count(case when was_relevant = true then 1 end) as relevant_count,
  count(case when was_relevant = false then 1 end) as irrelevant_count,
  round(
    100.0 * count(case when was_relevant = true then 1 end) / 
    nullif(count(case when was_relevant is not null then 1 end), 0),
    2
  ) as relevance_rate
from public.rag_query_log
group by date_trunc('day', created_at);

comment on view public.v_rag_performance is 'Métricas diárias de performance do RAG (similaridade, tempo, relevância)';

-- -----------------------------------------------------------------------------
-- VIEW: v_active_prompt
-- Prompt ativo atual para fácil consulta
-- -----------------------------------------------------------------------------

create view public.v_active_prompt as
select
  prompt_id,
  name,
  content,
  version,
  tokens_estimated,
  times_used,
  avg_accuracy,
  created_at
from public.agent_prompts
where is_active = true;

comment on view public.v_active_prompt is 'Prompts ativos para uso imediato pelo agente';

-- -----------------------------------------------------------------------------
-- VIEW: v_chunks_by_category
-- Resumo de chunks por categoria
-- -----------------------------------------------------------------------------

create view public.v_chunks_by_category as
select
  category,
  count(*) as total_chunks,
  sum(tokens_count) as total_tokens,
  avg(tokens_count) as avg_tokens_per_chunk,
  array_agg(distinct source_section) as sections
from public.rag_chunks
where is_active = true
group by category;

comment on view public.v_chunks_by_category is 'Resumo de chunks agrupados por categoria';
