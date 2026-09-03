"""
Gera 5 conversas reais com o agente e grava em examples/*.md
para o entregável do desafio Artefact.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agent import Agent

OUT_DIR = Path(__file__).parent.parent / "examples"
TZ = ZoneInfo("America/Campo_Grande")

SCENARIOS: list[dict] = [
    {
        "file": "01_catalogo_violoes.md",
        "title": "Consulta ao catálogo — violões até R$1.000",
        "turns": [
            "Oi! Quais violões vocês têm disponíveis custando até R$1000?",
        ],
    },
    {
        "file": "02_endereco_loja.md",
        "title": "Informações gerais — endereço da loja",
        "turns": [
            "Qual o endereço da loja?",
        ],
    },
    {
        "file": "03_preco_takamine.md",
        "title": "Consulta de preço — Takamine GD20",
        "turns": [
            "Quanto custa o Takamine GD20?",
        ],
    },
    {
        "file": "04_politica_devolucao.md",
        "title": "Política de devolução — situação não trivial",
        "turns": [
            "Me arrependi da minha compra, posso devolver meu pedido?",
            "Comprei online há 10 dias, ainda dá?",
        ],
    },
    {
        "file": "05_fora_do_escopo.md",
        "title": "Fora do escopo — pergunta não relacionada à loja",
        "turns": [
            "Vocês recomendam algum app pra aprender a tocar guitarra?",
            "E aula particular, vocês oferecem?",
        ],
    },
]


def format_meta(response) -> str:
    parts = [
        f"modelo: {response.model_used}",
        f"tokens: {response.tokens_input}↑ {response.tokens_output}↓",
        f"tempo: {response.response_time_ms}ms",
    ]
    if response.rag_chunks_used:
        parts.append(f"RAG chunks: {response.rag_chunks_used}")
    return " | ".join(parts)


def run_scenario(scenario: dict) -> str:
    agent = Agent(channel="examples")
    now = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    lines: list[str] = [
        f"# {scenario['title']}",
        "",
        f"*Sessão gerada em: {now} (America/Campo_Grande)*",
        "",
        "---",
        "",
    ]

    for user_msg in scenario["turns"]:
        response = agent.chat(user_msg)
        lines.append(f"**Usuário:** {user_msg}")
        lines.append("")
        lines.append(f"**Agente:** {response.content}")
        lines.append("")
        lines.append(f"*{format_meta(response)}*")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Remove exemplo antigo de devolução se o nome mudou
    legacy = OUT_DIR / "02_politica_devolucao.md"
    # Mantemos 04 como devolução; se existir 02 antigo de política, será sobrescrito por endereco

    for scenario in SCENARIOS:
        print(f"-> {scenario['file']} ...", flush=True)
        md = run_scenario(scenario)
        path = OUT_DIR / scenario["file"]
        path.write_text(md, encoding="utf-8")
        print(f"  saved: {path}", flush=True)

    obsolete = [
        "02_politica_devolucao.md",
        "03_preco_produto_especifico.md",
        "04_status_pedido.md",
    ]
    keep = {s["file"] for s in SCENARIOS}
    for name in obsolete:
        p = OUT_DIR / name
        if p.exists() and name not in keep:
            p.unlink()
            print(f"  removed legacy: {p.name}", flush=True)

    print("OK - 5 conversas geradas.", flush=True)


if __name__ == "__main__":
    main()
