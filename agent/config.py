"""
Configurações do agente.
Carrega variáveis de ambiente do .env
"""

from pathlib import Path
from dataclasses import dataclass


def load_env(path: Path) -> dict[str, str]:
    """Carrega variáveis do arquivo .env"""
    env = {}
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
ENV = load_env(PROJECT_ROOT / ".env")


@dataclass
class Config:
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dims: int = 1536
    llm_model: str = "gpt-4o-mini"
    rag_match_count: int = 3
    rag_similarity_threshold: float = 0.5

    @classmethod
    def from_env(cls) -> "Config":
        supabase_url = ENV.get("SUPABASE_REST_URL", "")
        supabase_key = ENV.get("SUPABASE_KEY", "")
        openai_api_key = ENV.get("OPENAI_API_KEY", "")

        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_REST_URL e SUPABASE_KEY sao obrigatorios no .env")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY e obrigatoria no .env")

        return cls(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            openai_api_key=openai_api_key,
        )


config = Config.from_env()
