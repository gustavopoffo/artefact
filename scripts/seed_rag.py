"""
Script para popular o RAG no Supabase.
Gera embeddings dos chunks e insere nas tabelas agent_prompts e rag_chunks.
"""

import os
import json
import hashlib
import httpx
from pathlib import Path

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


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


ENV = load_env(ENV_PATH)

SUPABASE_URL = ENV.get("SUPABASE_REST_URL", "")
SUPABASE_KEY = ENV.get("SUPABASE_KEY", "")
OPENAI_API_KEY = ENV.get("OPENAI_API_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_REST_URL e SUPABASE_KEY são obrigatórios no .env")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY é obrigatório no .env")


# -----------------------------------------------------------------------------
# Funções de API
# -----------------------------------------------------------------------------

def supabase_request(
    method: str,
    table: str,
    data: dict | list | None = None,
    params: dict | None = None,
) -> dict | list:
    """Faz requisição ao Supabase REST API"""
    url = f"{SUPABASE_URL}/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    
    with httpx.Client(timeout=30) as client:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params,
        )
        
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase error: {response.status_code} - {response.text}")
        
        if response.text:
            return response.json()
        return {}


def generate_embedding(text: str) -> list[float]:
    """Gera embedding usando OpenAI API"""
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text,
        "dimensions": EMBEDDING_DIMENSIONS,
    }
    
    with httpx.Client(timeout=30) as client:
        response = client.post(url, headers=headers, json=payload)
        
        if response.status_code >= 400:
            raise RuntimeError(f"OpenAI error: {response.status_code} - {response.text}")
        
        data = response.json()
        return data["data"][0]["embedding"]


def count_tokens_estimate(text: str) -> int:
    """Estimativa simples de tokens (1 token ≈ 4 caracteres para português)"""
    return len(text) // 3


def content_hash(text: str) -> str:
    """Gera SHA256 do conteúdo"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Dados: System Prompt (arquivo versionado em prompts/)
# -----------------------------------------------------------------------------

PROMPT_VERSION = "2.1.2"
PROMPT_FILE = PROMPTS_DIR / f"system_prompt_v{PROMPT_VERSION}.md"


def load_system_prompt() -> str:
    """Carrega o system prompt da versão ativa a partir do arquivo markdown."""
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Prompt não encontrado: {PROMPT_FILE}")
    return PROMPT_FILE.read_text(encoding="utf-8").strip()


# -----------------------------------------------------------------------------
# Dados: Chunks RAG
# -----------------------------------------------------------------------------

RAG_CHUNKS = [
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Formas de Pagamento",
        "source_subsection": None,
        "section_number": "3.0",
        "chunk_index": 0,
        "category": "pagamento",
        "keywords": ["pagamento", "pix", "cartão", "débito", "crédito", "boleto", "desconto", "à vista"],
        "content": """A Empório da Música aceita as seguintes formas de pagamento para compras presenciais e online:

- PIX: Pagamento à vista com 5% de desconto sobre o preço de tabela.
- Cartão de Débito: Pagamento à vista. Todas as bandeiras aceitas.
- Cartão de Crédito: Parcelamento em até 12x sem juros. Parcela mínima de R$ 100,00.
- Boleto Bancário: Pagamento à vista. Compensação em até 3 dias úteis.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Formas de Pagamento",
        "source_subsection": "Regras de Parcelamento",
        "section_number": "3.1",
        "chunk_index": 1,
        "category": "pagamento",
        "keywords": ["parcelamento", "parcela", "juros", "crédito", "valor mínimo", "combinar pagamento"],
        "content": """Regras de Parcelamento no Cartão de Crédito:

- Parcelamento em até 3x: sem juros, sem valor mínimo de parcela (exceto abaixo de R$ 50,00).
- Parcelamento de 4x a 6x: sem juros, parcela mínima de R$ 80,00.
- Parcelamento de 7x a 12x: sem juros, parcela mínima de R$ 100,00.
- Combinação de formas de pagamento: permitida (ex.: PIX + cartão) para compras acima de R$ 2.000,00.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Política de Trocas e Devoluções",
        "source_subsection": "Direito de Arrependimento",
        "section_number": "4.0",
        "chunk_index": 0,
        "category": "troca",
        "keywords": ["arrependimento", "devolução", "7 dias", "online", "reembolso", "frete devolução"],
        "content": """Direito de Arrependimento para Compras Online:

- O cliente pode solicitar a devolução em até 7 (sete) dias corridos após o recebimento do produto, sem necessidade de justificativa.
- O produto deve estar em sua embalagem original, sem sinais de uso, com todos os acessórios e manuais.
- O reembolso será realizado na mesma forma de pagamento original em até 10 dias úteis.
- O frete de devolução é por conta da loja em caso de arrependimento.

Conforme o Código de Defesa do Consumidor (Lei nº 8.078/90).""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Política de Trocas e Devoluções",
        "source_subsection": "Trocas por Defeito",
        "section_number": "4.1",
        "chunk_index": 1,
        "category": "troca",
        "keywords": ["defeito", "fabricação", "30 dias", "garantia", "troca defeito", "mau uso"],
        "content": """Trocas por Defeito de Fabricação:

- Produtos com defeito de fabricação podem ser trocados em até 30 (trinta) dias corridos após a compra.
- Após os 30 dias, o cliente deve acionar a garantia diretamente com o fabricante. A Empório da Música pode intermediar o processo mediante solicitação.

NÃO SÃO COBERTOS:
- Danos causados por mau uso
- Danos por quedas
- Exposição a umidade excessiva
- Modificações não autorizadas""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Política de Trocas e Devoluções",
        "source_subsection": "Trocas por Preferência",
        "section_number": "4.2",
        "chunk_index": 2,
        "category": "troca",
        "keywords": ["troca preferência", "cor", "modelo", "tamanho", "7 dias", "diferença valor"],
        "content": """Trocas por Preferência (cor, modelo, tamanho):

- Permitidas em até 7 dias após a compra.
- Sujeitas à disponibilidade do produto desejado.
- O produto deve estar em perfeito estado e na embalagem original.
- Diferenças de valor serão cobradas ou reembolsadas conforme o caso.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Política de Trocas e Devoluções",
        "source_subsection": "Itens Não Elegíveis",
        "section_number": "4.3",
        "chunk_index": 3,
        "category": "troca",
        "keywords": ["não troca", "personalização", "liquidação", "venda final", "boquilha", "sopro", "higiene"],
        "content": """Itens que NÃO podem ser trocados:

- Instrumentos com personalização ou ajustes sob encomenda (setup, regulagem especial).
- Produtos adquiridos em promoções de liquidação com aviso explícito de "venda final".
- Boquilhas de instrumentos de sopro, por questões de higiene.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Política de Frete e Entregas",
        "source_subsection": "Região Metropolitana de Campo Grande",
        "section_number": "5.0",
        "chunk_index": 0,
        "category": "frete",
        "keywords": ["frete grátis", "Campo Grande", "motoboy", "entrega local", "R$ 500", "R$ 35"],
        "content": """Entregas na Região Metropolitana de Campo Grande:

- Frete grátis para pedidos acima de R$ 500,00.
- Para pedidos abaixo de R$ 500,00, taxa fixa de R$ 35,00.
- Prazo de entrega: 1 a 3 dias úteis.
- Entrega realizada por motoboy próprio. O cliente será contactado por telefone antes da entrega.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Política de Frete e Entregas",
        "source_subsection": "Outras Cidades",
        "section_number": "5.1",
        "chunk_index": 1,
        "category": "frete",
        "keywords": ["Correios", "PAC", "SEDEX", "Jadlog", "transportadora", "prazo", "rastreamento", "seguro"],
        "content": """Entregas para Outras Cidades (fora da região metropolitana de Campo Grande):

Utilizamos Correios (PAC e SEDEX) e transportadora Jadlog.

| Modalidade | Prazo Estimado | Rastreamento | Seguro |
|------------|----------------|--------------|--------|
| PAC (Correios) | 5 a 12 dias úteis | Sim | Incluído |
| SEDEX (Correios) | 2 a 5 dias úteis | Sim | Incluído |
| Jadlog (.package) | 3 a 8 dias úteis | Sim | Incluído |

- O valor do frete é calculado com base no CEP de destino, peso e dimensões.
- Instrumentos de grande porte (baterias, pianos digitais, contrabaixos) podem exigir frete especial com cotação individual.
- Todos os envios incluem seguro contra extravios e danos.
- Em caso de avaria, o cliente deve recusar o recebimento e entrar em contato imediatamente.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Política de Frete e Entregas",
        "source_subsection": "Código de Rastreamento",
        "section_number": "5.2",
        "chunk_index": 2,
        "category": "frete",
        "keywords": ["rastreamento", "código", "rastrear", "pedido", "enviado", "despachado"],
        "content": """Código de Rastreamento:

- Enviado automaticamente por e-mail e WhatsApp assim que o pedido é despachado.
- Formato padrão: BR seguido de 9 caracteres alfanuméricos e BR (exemplo: BR4K7M2X9P1BR).
- Pode ser consultado diretamente no site dos Correios ou da Jadlog.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Promoções e Descontos",
        "source_subsection": "Tipos de Promoção",
        "section_number": "6.0",
        "chunk_index": 0,
        "category": "promocao",
        "keywords": ["promoção", "desconto", "Black Friday", "aniversário", "volta às aulas", "queima estoque"],
        "content": """Principais Campanhas Promocionais da Empório da Música:

- Aniversário da Loja (Agosto): descontos de 10% a 25% em itens selecionados.
- Black Friday (Novembro): descontos de 15% a 30% em todo o catálogo.
- Volta às Aulas (Fevereiro): descontos especiais em instrumentos para estudantes.
- Queima de Estoque: promoções pontuais para renovação de catálogo.
- Semana do Músico: promoções na semana do Dia do Músico (22 de novembro).""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Promoções e Descontos",
        "source_subsection": "Regras de Promoções",
        "section_number": "6.1",
        "chunk_index": 1,
        "category": "promocao",
        "keywords": ["cumulativo", "desconto PIX", "estoque", "rain check", "preço promocional"],
        "content": """Regras de Promoções:

CUMULATIVIDADE: Promoções NÃO são cumulativas. O desconto de PIX (5%) não se aplica sobre preços já promocionais.

ESTOQUE: Promoções estão sujeitas à disponibilidade de estoque. Produtos esgotados durante a promoção não geram direito a rain check (reserva de preço).

COMUNICAÇÃO: Preços promocionais devem sempre ser apresentados junto ao preço original e o percentual de desconto, para total transparência.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Garantia",
        "source_subsection": "Garantia Legal e do Fabricante",
        "section_number": "8.0",
        "chunk_index": 0,
        "category": "garantia",
        "keywords": ["garantia", "90 dias", "fabricante", "defeito", "6 meses", "2 anos", "CDC"],
        "content": """Garantia dos Produtos:

GARANTIA LEGAL (CDC):
- Todos os produtos possuem garantia legal de 90 (noventa) dias contra defeitos de fabricação.
- Contados a partir da data de recebimento pelo cliente.

GARANTIA DO FABRICANTE:
- Além da garantia legal, a maioria dos fabricantes oferece garantia própria de 6 meses a 2 anos.
- Prazos e condições específicos estão no certificado de garantia que acompanha cada produto.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Garantia",
        "source_subsection": "Exclusões da Garantia",
        "section_number": "8.1",
        "chunk_index": 1,
        "category": "garantia",
        "keywords": ["não cobre", "desgaste", "mau uso", "queda", "modificação", "terceiros"],
        "content": """O que NÃO é coberto pela garantia:

- Desgaste natural de peças (trastes, cordas, feltros, palhetas de sopro).
- Danos por mau uso, queda, exposição a condições climáticas extremas.
- Modificações ou reparos realizados por terceiros não autorizados.
- Danos estéticos que não afetem a funcionalidade do instrumento.""",
    },
    {
        "source_document": "politicas_da_loja.pdf",
        "source_section": "Privacidade e Proteção de Dados",
        "source_subsection": "LGPD",
        "section_number": "9.0",
        "chunk_index": 0,
        "category": "lgpd",
        "keywords": ["LGPD", "dados pessoais", "privacidade", "exclusão", "consentimento", "Lei 13.709"],
        "content": """Privacidade e Proteção de Dados (LGPD):

A Empório da Música está em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018).

Os dados pessoais coletados (nome, telefone, e-mail, endereço) são utilizados exclusivamente para:
- Processamento e entrega de pedidos.
- Comunicação sobre status de pedidos e rastreamento.
- Envio de promoções e novidades (mediante consentimento explícito).
- Cumprimento de obrigações legais e fiscais.

DIREITOS DO CLIENTE:
- Dados NÃO são compartilhados com terceiros para fins de marketing.
- O cliente pode solicitar a exclusão de seus dados a qualquer momento via WhatsApp ou e-mail.""",
    },
]


# -----------------------------------------------------------------------------
# Execução Principal
# -----------------------------------------------------------------------------

def seed_prompt():
    """Insere o system prompt versionado (arquivo em prompts/) e ativa."""
    print(f"\n[1/3] Inserindo System Prompt v{PROMPT_VERSION}...")

    content = load_system_prompt()

    existing = supabase_request(
        "GET",
        "agent_prompts",
        params={
            "name": "eq.system_prompt",
            "version": f"eq.{PROMPT_VERSION}",
            "select": "prompt_id,tokens_estimated,is_active",
        },
    )
    if existing:
        row = existing[0]
        if not row.get("is_active"):
            supabase_request(
                "PATCH",
                "agent_prompts",
                {"is_active": True},
                params={"prompt_id": f"eq.{row['prompt_id']}"},
            )
            print(f"    OK Prompt ja existia — reativado: {row['prompt_id']}")
        else:
            print(f"    OK Prompt ja existe e esta ativo: {row['prompt_id']}")
        return row

    prompt_data = {
        "name": "system_prompt",
        "description": (
            "v2.1.2 — exemplos completos, sem markdown **, emoji moderado"
        ),
        "content": content,
        "version": PROMPT_VERSION,
        "is_active": True,
        "tokens_estimated": count_tokens_estimate(content),
    }

    result = supabase_request("POST", "agent_prompts", prompt_data)
    print(f"    OK Prompt inserido: {result[0]['prompt_id']}")
    print(f"    OK Tokens estimados: {prompt_data['tokens_estimated']}")
    return result[0]


def seed_chunks():
    """Insere os chunks na tabela rag_chunks com embeddings"""
    print("\n[2/3] Gerando embeddings e inserindo chunks...")
    
    total = len(RAG_CHUNKS)
    inserted = []
    
    for i, chunk in enumerate(RAG_CHUNKS, 1):
        print(f"    [{i}/{total}] {chunk['section_number']} - {chunk['source_section']}", end="")

        hash_value = content_hash(chunk["content"])
        existing = supabase_request(
            "GET",
            "rag_chunks",
            params={"content_hash": f"eq.{hash_value}", "select": "chunk_id,tokens_count"},
        )
        if existing:
            inserted.append(existing[0])
            print(f" SKIP (ja existe, {existing[0].get('tokens_count', '?')} tokens)")
            continue
        
        # Gerar embedding
        embedding = generate_embedding(chunk["content"])
        
        # Preparar dados
        chunk_data = {
            "content": chunk["content"],
            "content_hash": hash_value,
            "embedding": embedding,
            "source_document": chunk["source_document"],
            "source_section": chunk["source_section"],
            "source_subsection": chunk["source_subsection"],
            "section_number": chunk["section_number"],
            "chunk_index": chunk["chunk_index"],
            "total_chunks_in_section": None,  # Calcular depois
            "tokens_count": count_tokens_estimate(chunk["content"]),
            "category": chunk["category"],
            "keywords": chunk["keywords"],
            "is_active": True,
        }
        
        result = supabase_request("POST", "rag_chunks", chunk_data)
        inserted.append(result[0])
        print(f" OK ({chunk_data['tokens_count']} tokens)")
    
    return inserted


def update_chunk_totals():
    """Atualiza o campo total_chunks_in_section para cada chunk"""
    print("\n[3/3] Atualizando totais por seção...")
    
    # Buscar todos os chunks
    chunks = supabase_request("GET", "rag_chunks", params={"select": "chunk_id,source_section"})
    
    # Contar por seção
    section_counts = {}
    for chunk in chunks:
        section = chunk["source_section"]
        section_counts[section] = section_counts.get(section, 0) + 1
    
    # Atualizar cada chunk
    for section, count in section_counts.items():
        supabase_request(
            "PATCH",
            "rag_chunks",
            {"total_chunks_in_section": count},
            params={"source_section": f"eq.{section}"}
        )
        print(f"    OK {section}: {count} chunks")


def main():
    print("=" * 60)
    print("SEED RAG — Empório da Música")
    print("=" * 60)
    
    try:
        seed_prompt()
        seed_chunks()
        update_chunk_totals()
        
        print("\n" + "=" * 60)
        print("SEED COMPLETO!")
        print("=" * 60)
        
        print("\nResumo:")
        print("  - Prompts: verificar no Supabase (agent_prompts)")
        print("  - Chunks: verificar no Supabase (rag_chunks)")
        
    except Exception as e:
        print(f"\nERRO: {e}")
        raise


if __name__ == "__main__":
    main()
