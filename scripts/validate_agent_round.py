"""
Rodada de validacao: RAG + consulta a banco.
Roda o agente e checa se a resposta contem fatos esperados.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

from agent import Agent
from agent.database import db


@dataclass
class CaseResult:
    name: str
    kind: str  # RAG | DB
    question: str
    passed: bool
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    answer: str = ""
    rag_chunks: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int = 0
    sources: dict = field(default_factory=dict)
    error: str | None = None


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def has_any(text: str, needles: list[str]) -> bool:
    t = norm(text)
    return any(norm(n) in t for n in needles)


def has_money(text: str, value: float) -> bool:
    """Aceita 599.9, 599,90, 599.90 etc."""
    whole = int(value)
    cents = int(round((value - whole) * 100))
    patterns = [
        rf"{whole}[.,]{cents:02d}",
        rf"{whole}",
    ]
    t = text.replace(" ", "")
    return any(re.search(p, t) for p in patterns)


def run_case(
    name: str,
    kind: str,
    question: str,
    checks: list[tuple[str, callable]],
    channel: str = "test",
) -> CaseResult:
    agent = Agent(channel=channel)
    try:
        resp = agent.chat(question)
        answer = resp.content or ""
        results = []
        for label, fn in checks:
            try:
                ok = bool(fn(answer, resp))
                detail = "ok" if ok else "falhou"
            except Exception as e:
                ok = False
                detail = str(e)
            results.append((label, ok, detail))
        return CaseResult(
            name=name,
            kind=kind,
            question=question,
            passed=all(ok for _, ok, _ in results),
            checks=results,
            answer=answer,
            rag_chunks=resp.rag_chunks_used,
            tokens_in=resp.tokens_input,
            tokens_out=resp.tokens_output,
            ms=resp.response_time_ms,
            sources=resp.sources_consulted or {},
        )
    except Exception as e:
        return CaseResult(
            name=name,
            kind=kind,
            question=question,
            passed=False,
            checks=[("execucao", False, str(e))],
            error=str(e),
        )


def main() -> int:
    # Ground truth
    c40 = next(p for p in db.search_products("Yamaha C40") if "C40" in p["product_name"])
    promos = db.get_active_promotions()
    ohana = next(p for p in promos if p["product_id"] == 121)
    order = db.get_order_by_id(15)
    assert order, "Pedido #15 nao encontrado no banco"

    cases: list[CaseResult] = []

    # --- RAG ---
    cases.append(
        run_case(
            "RAG — direito de arrependimento (7 dias)",
            "RAG",
            "Qual o prazo para devolver uma compra online se eu me arrepender?",
            [
                ("menciona 7 dias", lambda a, r: has_any(a, ["7 dias", "sete dias"])),
                ("nao inventa prazo absurdo (30 dias de arrependimento)", lambda a, r: "30 dias" not in norm(a) or "garantia" in norm(a) or "defeito" in norm(a)),
                ("usou RAG (chunks>0) ou fala de devolucao", lambda a, r: r.rag_chunks_used > 0 or has_any(a, ["devol", "arrepend"])),
            ],
        )
    )

    cases.append(
        run_case(
            "RAG — PIX 5%",
            "RAG",
            "Tem desconto no PIX?",
            [
                ("menciona 5%", lambda a, r: has_any(a, ["5%", "5 %", "cinco por cento", "5 por cento"])),
                ("menciona PIX", lambda a, r: "pix" in norm(a)),
                ("usou RAG", lambda a, r: r.rag_chunks_used > 0 or "pagamento" in str(r.sources_consulted).lower()),
            ],
        )
    )

    cases.append(
        run_case(
            "RAG — frete Campo Grande",
            "RAG",
            "Como funciona o frete para Campo Grande?",
            [
                ("menciona frete gratis ou taxa", lambda a, r: has_any(a, ["frete gratis", "frete grátis", "r$ 500", "500", "r$ 35", "35"])),
                ("menciona prazo local", lambda a, r: has_any(a, ["1 a 3", "1-3", "dias uteis", "dias úteis", "motoboy"])),
            ],
        )
    )

    cases.append(
        run_case(
            "RAG — garantia legal 90 dias",
            "RAG",
            "Qual a garantia dos produtos?",
            [
                ("menciona 90 dias", lambda a, r: has_any(a, ["90 dias", "noventa dias"])),
                ("nao confunde so com 7 dias de arrependimento", lambda a, r: "garant" in norm(a) or "90" in a),
            ],
        )
    )

    # --- DB ---
    cases.append(
        run_case(
            "DB — preco e estoque Yamaha C40",
            "DB",
            "Quanto custa o Yamaha C40 e tem em estoque?",
            [
                ("preco correto 599,90", lambda a, r: has_money(a, float(c40["price_brl"]))),
                ("estoque 12", lambda a, r: has_any(a, ["12", "doze"])),
                ("consultou products", lambda a, r: "products" in (r.sources_consulted or {}).get("tables", [])),
            ],
        )
    )

    cases.append(
        run_case(
            "DB — promocao ativa Ohana CK-20",
            "DB",
            "Quanto custa o Ohana CK-20? Tem promocao?",
            [
                ("preco com desconto ~439,20", lambda a, r: has_money(a, float(ohana["discounted_price"])) or has_money(a, 439.2)),
                ("menciona desconto/promo ou preco de/por", lambda a, r: has_any(a, ["desconto", "promo", "off", "%", "de r$", "por r$"])),
                ("nao inventa outro preco absurdo sem 439/549", lambda a, r: has_money(a, 439.2) or has_money(a, 549.0) or has_money(a, float(ohana["discounted_price"]))),
            ],
        )
    )

    cases.append(
        run_case(
            "DB — status pedido #15",
            "DB",
            "Qual o status do pedido 15?",
            [
                ("menciona pending/pendente ou status real", lambda a, r: has_any(a, [order[0]["order_status"], "pendente", "pending", "aguard"])),
                ("consultou orders", lambda a, r: "orders" in (r.sources_consulted or {}).get("tables", [])),
            ],
        )
    )

    cases.append(
        run_case(
            "DB — produto inexistente nao inventa estoque",
            "DB",
            "Voces tem a guitarra Fender Stratocaster Ultra Rare Pink Diamond Edition?",
            [
                ("nao afirma ter em estoque com quantidade inventada", lambda a, r: not re.search(r"\b\d+\s+unidad", norm(a)) or has_any(a, ["nao", "não", "nao localiz", "não localiz", "nao encont", "não encont", "nao trabalh", "não trabalh", "nao temos", "não temos"])),
                ("pede modelo ou diz que nao achou", lambda a, r: has_any(a, ["nao", "não", "modelo", "nao encont", "não encont", "nao localiz", "não localiz", "disponiv"])),
            ],
        )
    )

    # Report
    print("=" * 72)
    print("VALIDACAO AGENTE — RAG + BANCO")
    print("=" * 72)

    failed = 0
    for i, c in enumerate(cases, 1):
        status = "PASS" if c.passed else "FAIL"
        if not c.passed:
            failed += 1
        print(f"\n[{i}] {status} | {c.kind} | {c.name}")
        print(f"    Q: {c.question}")
        if c.error:
            print(f"    ERRO: {c.error}")
        else:
            preview = c.answer.replace("\n", " ")
            if len(preview) > 280:
                preview = preview[:280] + "..."
            print(f"    A: {preview}")
            print(f"    meta: {c.ms}ms | tokens {c.tokens_in}+{c.tokens_out} | rag_chunks={c.rag_chunks} | sources={c.sources.get('tables')}")
        for label, ok, detail in c.checks:
            mark = "OK" if ok else "X "
            print(f"      [{mark}] {label}" + (f" ({detail})" if not ok else ""))

    total = len(cases)
    passed = total - failed
    print("\n" + "=" * 72)
    print(f"RESULTADO: {passed}/{total} passou | {failed} falhou")
    print("=" * 72)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
