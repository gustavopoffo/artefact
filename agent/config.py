"""
Configurações do agente.
Carrega variáveis do ambiente do sistema e, em seguida, do arquivo .env local
(valores do .env sobrescrevem só se a env do sistema estiver vazia — prioridade: os.environ).
"""

import os
from pathlib import Path
from dataclasses import dataclass


def load_env_file(path: Path) -> dict[str, str]:
    """Carrega variáveis do arquivo .env (sem sobrescrever o processo)."""
    env: dict[str, str] = {}
    if not path.exists():
        return env

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")

    return env


PROJECT_ROOT = Path(__file__).parent.parent
FILE_ENV = load_env_file(PROJECT_ROOT / ".env")


def env(key: str, default: str = "") -> str:
    """Prioriza variável de ambiente do sistema (Render/Vercel); fallback .env local."""
    return os.environ.get(key) or FILE_ENV.get(key) or default


@dataclass
class Config:
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    frontend_origin: str = "*"
    embedding_model: str = "text-embedding-3-small"
    embedding_dims: int = 1536
    llm_model: str = "gpt-4o-mini"
    rag_match_count: int = 3
    rag_similarity_threshold: float = 0.5

    @classmethod
    def from_env(cls) -> "Config":
        supabase_url = env("SUPABASE_REST_URL")
        supabase_key = env("SUPABASE_KEY")
        openai_api_key = env("OPENAI_API_KEY")
        frontend_origin = env("FRONTEND_ORIGIN", "*")

        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_REST_URL e SUPABASE_KEY sao obrigatorios")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY e obrigatoria")

        return cls(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_api_key,
            frontend_origin=frontend_origin,
        )


config = Config.from_env()
