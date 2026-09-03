"""
Retrieval-Augmented Generation (RAG).
Busca chunks relevantes para a pergunta do usuário.
"""

import time
import httpx

from .config import config
from .embeddings import generate_embedding


class RAG:
    """Sistema de busca por similaridade semântica."""

    def __init__(self):
        self.base_url = config.supabase_url
        self.headers = {
            "apikey": config.supabase_key,
            "Authorization": f"Bearer {config.supabase_key}",
            "Content-Type": "application/json",
        }

    def search(
        self,
        query: str,
        match_count: int | None = None,
        similarity_threshold: float | None = None,
        filter_category: str | None = None,
    ) -> tuple[list[dict], dict]:
        """
        Busca chunks similares à query.

        Retorna:
            - Lista de chunks encontrados
            - Métricas da busca (para logging)
        """
        match_count = match_count or config.rag_match_count
        similarity_threshold = similarity_threshold or config.rag_similarity_threshold

        start_time = time.perf_counter()

        # Gera embedding da query
        query_embedding = generate_embedding(query)

        # Chama função match_chunks via RPC
        rpc_payload = {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "similarity_threshold": similarity_threshold,
        }
        if filter_category:
            rpc_payload["filter_category"] = filter_category

        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base_url}/rpc/match_chunks",
                headers=self.headers,
                json=rpc_payload,
            )

            if response.status_code >= 400:
                raise RuntimeError(f"RAG search error: {response.status_code} - {response.text}")

            chunks = response.json()

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Métricas
        metrics = {
            "query_text": query,
            "chunks_returned": [c["chunk_id"] for c in chunks],
            "chunks_count": len(chunks),
            "top_similarity": chunks[0]["similarity"] if chunks else None,
            "avg_similarity": sum(c["similarity"] for c in chunks) / len(chunks) if chunks else None,
            "search_time_ms": elapsed_ms,
            "filter_category": filter_category,
        }

        return chunks, metrics

    def format_context(self, chunks: list[dict]) -> str:
        """Formata chunks como contexto para o prompt."""
        if not chunks:
            return ""

        lines = ["## Informacoes das Politicas da Loja\n"]
        for chunk in chunks:
            section = chunk.get("source_section", "")
            subsection = chunk.get("source_subsection", "")
            content = chunk.get("content", "")

            header = f"### {section}"
            if subsection:
                header += f" > {subsection}"

            lines.append(header)
            lines.append(content)
            lines.append("")

        return "\n".join(lines)


rag = RAG()
