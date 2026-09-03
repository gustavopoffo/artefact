-- =============================================================================
-- MIGRATION: Remove tabela knowledge_sources (não usada)
-- Motivo: Substituída pela estrutura rag_chunks com metadados mais específicos
-- =============================================================================

drop table if exists public.knowledge_sources;

-- Adiciona função para incrementar uso do prompt
create or replace function public.increment_prompt_usage(p_prompt_id uuid)
returns void
language plpgsql
as $$
begin
  update public.agent_prompts
  set times_used = times_used + 1,
      updated_at = now()
  where prompt_id = p_prompt_id;
end;
$$;

comment on function public.increment_prompt_usage is 'Incrementa contador de uso de um prompt';

-- Adiciona função para atualizar message_id no rag_query_log
create or replace function public.update_rag_log_message(p_log_id uuid, p_message_id uuid)
returns void
language plpgsql
as $$
begin
  update public.rag_query_log
  set message_id = p_message_id
  where log_id = p_log_id;
end;
$$;

comment on function public.update_rag_log_message is 'Atualiza message_id no log de RAG após criar a mensagem';
