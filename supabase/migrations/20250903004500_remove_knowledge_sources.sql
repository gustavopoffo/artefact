-- =============================================================================
-- MIGRATION: Remove tabela knowledge_sources (não usada)
-- Motivo: Substituída pela estrutura rag_chunks com metadados mais específicos
-- =============================================================================

drop table if exists public.knowledge_sources;
