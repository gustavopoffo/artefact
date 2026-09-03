"""
Agente Conversacional — Empório da Música.

Camadas:
  config / runtime_settings → configuração
  database / embeddings / rag / llm → integrações
  chat → orquestração do atendimento
  main → CLI de teste
"""

from .chat import Agent

__all__ = ["Agent"]
