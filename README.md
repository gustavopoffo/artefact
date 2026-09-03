# Artefact — Agente Conversacional para E-commerce de Instrumentos Musicais

## Visão Geral do Projeto

Sistema completo de **agente conversacional com IA** para atendimento a clientes de uma loja de instrumentos musicais no Mato Grosso do Sul.

### O que o Agente faz

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENTE CONVERSACIONAL                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   CLIENTE pergunta:                                                         │
│   "Vocês têm violão Yamaha em estoque? Qual o preço?"                      │
│                                                                             │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         AGENTE IA                                    │  │
│   │                                                                      │  │
│   │   1. Consulta BANCO DE DADOS                                        │  │
│   │      → SELECT * FROM products WHERE name ILIKE '%yamaha%'           │  │
│   │      → Verifica stock_quantity, price_brl, status                   │  │
│   │                                                                      │  │
│   │   2. Consulta POLÍTICAS DA LOJA                                     │  │
│   │      → Condições de pagamento                                        │  │
│   │      → Prazo de entrega por cidade                                   │  │
│   │      → Política de troca/devolução                                   │  │
│   │                                                                      │  │
│   │   3. Verifica HISTÓRICO DO CLIENTE                                  │  │
│   │      → Já é cadastrado?                                              │  │
│   │      → Tem pedidos anteriores?                                       │  │
│   │      → Preferências de pagamento?                                    │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              ▼                                              │
│   AGENTE responde:                                                          │
│   "Temos 14 unidades do Yamaha F310 por R$ 699,90 e 8 do Yamaha C70         │
│    por R$ 849,00. Para Campo Grande, entregamos em até 5 dias úteis.        │
│    Parcelamos em até 12x no cartão!"                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Capacidades do Agente

| Funcionalidade | Fonte de Dados | Exemplo de Pergunta |
|----------------|----------------|---------------------|
| Consulta de estoque | `products.stock_quantity` | "Tem guitarra Fender disponível?" |
| Preços e promoções | `products`, `promotions` | "Qual o preço do ukulele Kala?" |
| Status de pedido | `orders`, `order_items` | "Onde está meu pedido #15?" |
| Cadastro de cliente | `customers` | "Meu email está cadastrado?" |
| Políticas da loja | `knowledge_sources` | "Qual o prazo de devolução?" |
| Formas de pagamento | Políticas + ENUMs | "Vocês parcelam em quantas vezes?" |

---

## Arquitetura do Sistema

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                         │
│                    (Chat Widget / App / WhatsApp)                             │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           AGENTE IA (LLM)                                     │
│                                                                               │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│   │  Interpretação  │───▶│    Consulta     │───▶│    Resposta     │          │
│   │   da pergunta   │    │   às fontes     │    │    gerada       │          │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘          │
│                                  │                                            │
└──────────────────────────────────┼────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
          ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
          │   SUPABASE  │  │  POLÍTICAS  │  │  HISTÓRICO  │
          │   (Banco)   │  │  (RAG/Docs) │  │   (Chats)   │
          │             │  │             │  │             │
          │ • products  │  │ • Prazos    │  │ • Sessões   │
          │ • customers │  │ • Trocas    │  │ • Mensagens │
          │ • orders    │  │ • Garantia  │  │ • Ratings   │
          │ • stock     │  │ • Pagamento │  │ • Métricas  │
          └─────────────┘  └─────────────┘  └─────────────┘
```

---

## Estrutura do Banco de Dados

### Diagrama de Relacionamento (ERD)

```
┌─────────────────┐
│   categories    │
├─────────────────┤
│ category_id PK  │───────────────────────────────────────┐
│ name            │                                       │
│ description     │                                       │
└─────────────────┘                                       │
                                                          │ 1:N
┌─────────────────┐       ┌─────────────────┐       ┌─────┴───────────┐
│    customers    │       │   promotions    │       │    products     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ customer_id PK  │──┐    │ promotion_id PK │       │ product_id PK   │──┐
│ name            │  │    │ product_id FK   │───────│ name            │  │
│ phone           │  │    │ discount_percent│  N:1  │ price_brl       │  │
│ email           │  │    │ description     │       │ category_id FK  │  │
│ city            │  │    │ is_active       │       │ stock_quantity  │  │
└─────────────────┘  │    └─────────────────┘       │ status          │  │
        │            │                              │ specs (JSONB)   │  │
        │            │ 1:N                          └─────────────────┘  │
        │            │                                                   │
        │ 1:N        │                                                   │
        │  ┌─────────┴──────────┐       ┌─────────────────┐              │
        │  │       orders       │       │   order_items   │              │
        │  ├────────────────────┤       ├─────────────────┤              │
        │  │ order_id PK        │───────│ order_item_id PK│              │
        │  │ customer_id FK     │  1:N  │ order_id FK     │              │
        │  │ order_date         │       │ product_id FK   │──────────────┘
        │  │ status             │       │ quantity        │       N:1
        │  │ total_brl          │       └─────────────────┘
        │  │ payment_method     │
        │  └────────────────────┘
        │
        │ 1:N (opcional)
        │
┌───────┴─────────────┐       ┌─────────────────────┐
│   chat_sessions     │       │   chat_messages     │
├─────────────────────┤       ├─────────────────────┤
│ session_id PK (UUID)│───────│ message_id PK (UUID)│
│ customer_id FK      │  1:N  │ session_id FK       │
│ started_at          │       │ role (user/assistant│
│ ended_at            │       │ content             │
│ status              │       │ created_at          │
│ channel             │       │ model_used          │
└─────────────────────┘       │ response_time_ms    │
                              │ rating              │
┌─────────────────────┐       │ sources_consulted   │
│  knowledge_sources  │       └─────────────────────┘
├─────────────────────┤
│ source_id PK (UUID) │
│ name                │
│ source_type         │
│ content             │
│ embedding_status    │
└─────────────────────┘
```

### Relacionamentos

| Origem | Destino | Cardinalidade | Descrição |
|--------|---------|---------------|-----------|
| `products.category_id` | `categories.category_id` | N:1 | Produto pertence a uma categoria |
| `promotions.product_id` | `products.product_id` | N:1 | Promoção aplica-se a um produto |
| `orders.customer_id` | `customers.customer_id` | N:1 | Pedido pertence a um cliente |
| `order_items.order_id` | `orders.order_id` | N:1 | Item pertence a um pedido |
| `order_items.product_id` | `products.product_id` | N:1 | Item referencia um produto |
| `chat_sessions.customer_id` | `customers.customer_id` | N:1 | Sessão pode pertencer a um cliente |
| `chat_messages.session_id` | `chat_sessions.session_id` | N:1 | Mensagem pertence a uma sessão |

---

## Tabelas do Sistema

### Domínio: E-commerce

#### `categories`
Categorias de instrumentos musicais.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `category_id` | integer | PK |
| `name` | text | Nome único |
| `description` | text | Descrição |

#### `customers`
Clientes da loja (MS).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `customer_id` | integer | PK |
| `name` | text | Nome completo |
| `phone` | text | (67) XXXXX-XXXX |
| `email` | text | Único |
| `city` | text | Cidade no MS |

#### `products`
Instrumentos musicais.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `product_id` | integer | PK |
| `name` | text | Marca + modelo |
| `price_brl` | numeric | Preço em R$ |
| `category_id` | integer | FK → categories |
| `stock_quantity` | integer | Estoque disponível |
| `status` | enum | `active`, `discontinued`, `coming_soon` |
| `specs` | jsonb | Especificações técnicas |

#### `promotions`
Descontos por produto.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `promotion_id` | integer | PK |
| `product_id` | integer | FK → products |
| `discount_percent` | numeric | 1-100% |
| `is_active` | boolean | Se está ativa |

#### `orders`
Pedidos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `order_id` | integer | PK |
| `customer_id` | integer | FK → customers |
| `order_date` | date | Data do pedido |
| `status` | enum | `pending`, `confirmed`, `shipped`, `delivered`, `cancelled` |
| `total_brl` | numeric | Valor total |
| `payment_method` | enum | `pix`, `boleto`, `debit`, `credit_3x/6x/12x` |

#### `order_items`
Itens dos pedidos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `order_item_id` | bigint | PK |
| `order_id` | integer | FK → orders |
| `product_id` | integer | FK → products |
| `quantity` | integer | Quantidade |

---

### Domínio: Controle do Agente

#### `chat_sessions`
Sessões de conversa com o agente.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `session_id` | uuid | PK |
| `customer_id` | integer | FK → customers (nullable) |
| `started_at` | timestamptz | Início da sessão |
| `ended_at` | timestamptz | Fim da sessão |
| `status` | enum | `active`, `ended`, `abandoned` |
| `channel` | text | `web`, `whatsapp`, etc. |
| `metadata` | jsonb | user_agent, ip, device |

**Por que `customer_id` é nullable?** O cliente pode iniciar uma conversa antes de se identificar. Quando ele informa email/telefone, vinculamos a sessão.

#### `chat_messages`
Mensagens individuais (cliente e IA).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `message_id` | uuid | PK |
| `session_id` | uuid | FK → chat_sessions |
| `role` | enum | `user` (cliente), `assistant` (IA), `system` |
| `content` | text | Texto da mensagem |
| `created_at` | timestamptz | **Timestamp exato** |
| `model_used` | text | Modelo de IA (gpt-4, claude-3) |
| `tokens_input` | integer | Tokens de entrada |
| `tokens_output` | integer | Tokens de saída |
| `response_time_ms` | integer | Tempo de resposta em ms |
| `sources_consulted` | jsonb | Fontes usadas pela IA |
| `rating` | enum | `positive`, `negative`, `neutral` |
| `rating_feedback` | text | Feedback do avaliador |
| `rated_at` | timestamptz | Quando foi avaliado |

**Por que armazenar métricas?**
- `response_time_ms` → Monitorar performance
- `tokens_*` → Controle de custo
- `sources_consulted` → Rastreabilidade
- `rating` + `rating_feedback` → **Validação de acurácia**

#### `knowledge_sources`
Fontes de conhecimento do agente.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `source_id` | uuid | PK |
| `name` | text | Identificador único |
| `source_type` | text | `document`, `policy`, `faq` |
| `content` | text | Conteúdo textual |
| `file_path` | text | Arquivo original |
| `embedding_status` | text | Status do embedding |

---

## Views para Acompanhamento

### E-commerce

| View | Descrição |
|------|-----------|
| `v_products_with_category` | Produtos + categoria |
| `v_products_with_active_promotion` | Produtos em promoção com preço final |
| `v_order_details` | Pedidos completos com itens |
| `v_sales_summary` | Vendas por produto |
| `v_customer_orders_summary` | Resumo por cliente |
| `v_inventory_status` | Alertas de estoque |

### Controle do Agente

| View | Descrição |
|------|-----------|
| `v_chat_sessions_summary` | Sessões com métricas (duração, mensagens, tokens) |
| `v_chat_conversation_history` | Histórico formatado para frontend |
| `v_customer_chat_history` | Interações por cliente |
| `v_agent_accuracy_metrics` | **Acurácia diária do agente** |
| `v_low_rated_responses` | Respostas negativas para revisão |

---

## Validação de Acurácia do Agente

### Como funciona

1. **Avaliação de respostas** — Cada resposta do agente pode receber rating (`positive`, `negative`, `neutral`)
2. **Feedback textual** — Avaliador pode explicar o que estava errado
3. **Métricas agregadas** — View `v_agent_accuracy_metrics` calcula:
   - % de respostas positivas (acurácia)
   - Tempo médio de resposta
   - Tokens consumidos

### Exemplo de consulta de acurácia

```sql
SELECT 
  date,
  model_used,
  total_responses,
  positive_ratings,
  negative_ratings,
  accuracy_percent,
  avg_response_time_ms
FROM v_agent_accuracy_metrics
ORDER BY date DESC;
```

### Exemplo de respostas para revisão

```sql
SELECT 
  user_question,
  assistant_response,
  rating_feedback,
  created_at
FROM v_low_rated_responses
ORDER BY created_at DESC
LIMIT 20;
```

---

## Arquitetura RAG e Versionamento de Prompts

O documento `data/políticas_da_loja.pdf` (8 páginas, 10 seções) contém as regras de negócio da loja. Antes de implementar qualquer código, foram tomadas 7 decisões de arquitetura, documentadas abaixo com a justificativa e o impacto de cada uma.

### Decisão 1 — Divisão entre System Prompt (fixo) e RAG (busca)

**O que foi decidido:** Nem todo o conteúdo do PDF foi tratado como RAG. O documento foi lido seção a seção e classificado em dois grupos:

| Vai para o **System Prompt** | Vai para o **RAG** |
|---|---|
| 1.2 Dados da Empresa | 3. Formas de Pagamento |
| 2. Horário de Funcionamento | 4. Trocas e Devoluções |
| 7. Atendimento via WhatsApp (tom, fluxo, condutas) | 5. Frete e Entregas |
| 10. Disposições Finais | 6. Promoções e Descontos |
| | 8. Garantia |
| | 9. LGPD |

**Por que:** As seções 1.2, 2, 7 e 10 definem **como o agente deve se comportar** (tom de voz, fluxo de atendimento, o que fazer em cada situação) — isso é usado em **100% das conversas**, independente da pergunta. Já as seções 3, 4, 5, 6, 8 e 9 são **regras de consulta** (parcelamento, prazo de troca, frete por cidade) — usadas apenas quando o cliente pergunta sobre aquele assunto específico.

**Impacto:**
- Colocar tudo no prompt fixo gastaria ~3.000+ tokens em **toda** requisição, mesmo em perguntas que não precisam dessa informação (ex.: "Vocês têm violão Yamaha?").
- Com a separação, o prompt fixo tem ~1.200 tokens e o RAG injeta só os 1-3 chunks relevantes (~150-300 tokens) para cada pergunta.
- Economia estimada de **60-70% em tokens de contexto** nas conversas que não tocam em política de troca/frete/pagamento.

### Decisão 2 — Extração manual do texto, sem OCR

**O que foi decidido:** O texto do PDF foi extraído diretamente (leitura de texto nativo), sem usar Docling ou qualquer pipeline de OCR.

**Por que:** O PDF já é um documento com texto selecionável — não é um scan/imagem. OCR existe para converter *imagem em texto*; aqui o texto já existe. Rodar OCR nesse caso adicionaria uma etapa que só introduz risco de erro de reconhecimento (ex.: confundir números como "R$ 100,00") sem nenhum ganho.

**Impacto:**
- Zero risco de erro de OCR em valores monetários, prazos e percentuais — que são justamente os dados mais sensíveis do documento (errar "7 dias" para "1 dias" por falha de OCR seria crítico).
- Chunking foi feito manualmente por decisão de projeto, não como limitação: para 8 páginas com estrutura conhecida, chunking curado bate chunker semântico automático em acurácia.
- Fica documentado como próximo passo (ver Decisão 7) usar Docling + chunker semântico quando houver documentos escaneados ou em maior volume, onde curadoria manual não escala.

### Decisão 3 — Granularidade dos chunks (14 chunks, 1 por sub-regra)

**O que foi decidido:** Cada chunk representa **uma regra de negócio autossuficiente**, não uma seção inteira do PDF. Por exemplo, a seção 4 (Trocas e Devoluções) foi dividida em 4 chunks: arrependimento, defeito, preferência e itens não elegíveis — em vez de 1 chunk único com a seção toda.

**Por que:** Se a seção inteira fosse 1 chunk, uma pergunta sobre "posso trocar por outra cor?" traria de volta também as regras de defeito de fabricação e itens não elegíveis — informação irrelevante que consome tokens e pode confundir o modelo na hora de formular a resposta. Com chunks pequenos e específicos, a busca por similaridade retorna **exatamente** a regra pedida.

**Impacto:**
- Precisão de recuperação mais alta: o embedding de "troca de cor" fica semanticamente próximo apenas do chunk 4.2, não dos outros 3.
- Cada chunk é curto (80-150 tokens), então mesmo trazendo `match_count=3`, o custo de contexto é baixo.
- Trade-off aceito: mais linhas na tabela `rag_chunks` (14 em vez de 6), mas isso não tem custo real em um banco vetorial.

### Decisão 4 — Categoria e keywords em cada chunk

**O que foi decidido:** Todo chunk tem um campo `category` (`pagamento`, `troca`, `frete`, `promocao`, `garantia`, `lgpd`) e um array `keywords` além do embedding.

**Por que:** Busca por embedding sozinha pode falhar em casos de baixa similaridade semântica mas alta similaridade lexical (ex.: sigla "PAC" ou "SEDEX"). A função `match_chunks` aceita `filter_category` como parâmetro — se o agente já identificou que a pergunta é sobre frete, a busca vetorial roda **só dentro da categoria `frete`**, eliminando falsos positivos de outras categorias antes mesmo do cálculo de similaridade.

**Impacto:**
- Reduz o espaço de busca quando a categoria é conhecida, aumentando a precisão do top-k.
- Keywords funcionam como rede de segurança para termos técnicos/siglas que embeddings genéricos às vezes não capturam bem.
- Base para o próximo passo evolutivo: um classificador leve (ou o próprio LLM) prever a categoria antes da busca vetorial.

### Decisão 5 — Modelo de embedding: OpenAI `text-embedding-3-small` (1536 dims)

**O que foi decidido:** Embeddings gerados com `text-embedding-3-small`, dimensão 1536, armazenados em `pgvector` com índice `ivfflat` (cosine distance).

**Por que:** É o modelo de embedding mais barato da OpenAI com qualidade suficiente para textos curtos e bem delimitados (nosso caso, com chunks de 80-150 tokens). O modelo maior (`text-embedding-3-large`, 3072 dims) tem custo ~6x maior e ganho de acurácia marginal para textos deste tamanho e domínio fechado (política de loja, não conhecimento aberto).

**Impacto:**
- Custo de geração de embeddings para os 14 chunks é irrelevante (< $0.001).
- Índice `ivfflat` escala bem até milhares de chunks — folga grande considerando que hoje temos 14.
- Caso a acurácia medida (ver Decisão 7) não seja suficiente, a migração para `text-embedding-3-large` é direta: basta trocar a dimensão da coluna e regerar os embeddings, sem mudar estrutura.

### Decisão 6 — Versionamento do System Prompt (tabela `agent_prompts`)

**O que foi decidido:** O prompt não fica hardcoded no código do agente. Ele é uma linha na tabela `agent_prompts`, com `name`, `version`, `content`, `is_active` e métricas (`times_used`, `avg_accuracy`). Um trigger garante que só existe 1 prompt `is_active=true` por `name`.

**Por que:** O usuário pediu explicitamente "versionamento impecável" porque o prompt vai ser ajustado iterativamente à medida que respostas reais forem avaliadas (rating na tabela `chat_messages`). Sem versionamento, cada ajuste no prompt sobrescreve o anterior e não há como comparar performance entre versões nem fazer rollback.

**Impacto:**
- Cada versão do prompt (`1.0.0`, `1.1.0`, ...) fica preservada com histórico.
- É possível cruzar `chat_messages.rating` com a versão do prompt ativa no momento da resposta, respondendo objetivamente "a versão 1.1.0 teve mais acurácia que a 1.0.0?".
- Rollback é trivial: reativar uma versão antiga (`is_active=true`) sem perder nenhuma versão.

### Decisão 7 — Log de todas as buscas RAG (tabela `rag_query_log`)

**O que foi decidido:** Toda busca vetorial feita pelo agente é registrada: pergunta original, chunks retornados, similaridade (top e média), tempo de busca, e um campo `was_relevant` para avaliação manual posterior.

**Por que:** O usuário pediu "porcentagem de acertividade perfeita" — isso não se mede uma vez, se mede continuamente. Sem log, não há como saber quais perguntas o RAG está respondendo mal, nem revisar se o `similarity_threshold` (hoje 0.5) está bem calibrado.

**Impacto:**
- A view `v_rag_performance` já calcula taxa de relevância diária a partir desse log — métrica objetiva de acurácia do RAG (distinta da acurácia do agente como um todo, medida em `chat_messages.rating`).
- Perguntas com baixa similaridade ficam visíveis para virar novos chunks (gap de cobertura do documento).
- Base de dados real para decidir se vale investir em Docling + chunker automático (Decisão 2) quando o volume de documentos crescer.

---

## Fluxo de Execução do Agente (Ponta a Ponta)

Este diagrama mostra exatamente o que acontece em cada etapa de uma conversa, quais tabelas são lidas e escritas, e como os dados fluem pelo sistema.

### Mapa de Tabelas por Domínio

| Domínio | Tabela | Propósito | Agente Lê | Agente Escreve |
|---------|--------|-----------|-----------|----------------|
| E-commerce | `products` | Instrumentos à venda | ✓ | - |
| E-commerce | `categories` | Tipos de instrumento | ✓ | - |
| E-commerce | `promotions` | Descontos ativos | ✓ | - |
| E-commerce | `customers` | Clientes cadastrados | ✓ | - |
| E-commerce | `orders` | Pedidos | ✓ | - |
| E-commerce | `order_items` | Itens dos pedidos | ✓ | - |
| Agente | `chat_sessions` | Sessões de conversa | ✓ | ✓ |
| Agente | `chat_messages` | Mensagens user/assistant | ✓ | ✓ |
| Agente | `agent_prompts` | Prompts versionados | ✓ | métricas |
| RAG | `rag_chunks` | Chunks com embedding | `match_chunks()` | - |
| RAG | `rag_query_log` | Log de buscas | - | ✓ |

### Diagrama do Fluxo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FLUXO DE UMA CONVERSA                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. INÍCIO DA SESSÃO
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ INSERT INTO chat_sessions (channel, status, metadata)                    │
   │ → session_id = UUID gerado                                               │
   │ → customer_id = NULL (cliente ainda não identificado)                    │
   └──────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ SELECT content FROM v_active_prompt WHERE name = 'system_prompt'         │
   │ → Carrega o prompt ativo (v1.0.0, ~1243 tokens)                          │
   └──────────────────────────────────────────────────────────────────────────┘

2. CLIENTE ENVIA MENSAGEM ("Vocês têm violão Yamaha?")
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ INSERT INTO chat_messages (session_id, role='user', content)             │
   └──────────────────────────────────────────────────────────────────────────┘

3. AGENTE PROCESSA (em paralelo)
   ┌──────────────────────┐                         ┌──────────────────────┐
   │ EMBEDDING DA QUERY   │                         │ CONSULTA AO BANCO    │
   │ OpenAI API           │                         │ SELECT * FROM        │
   │ text-embedding-3     │                         │ products WHERE name  │
   │ → vetor 1536 dims    │                         │ ILIKE '%yamaha%'     │
   └──────────────────────┘                         └──────────────────────┘
            │                                                  │
            ▼                                                  │
   ┌──────────────────────┐                                    │
   │ SELECT * FROM        │                                    │
   │ match_chunks(        │                                    │
   │   embedding,         │  ← Se pergunta for sobre           │
   │   match_count=3,     │    "troca", "frete", "pagamento"   │
   │   threshold=0.5      │    → retorna chunks relevantes     │
   │ )                    │                                    │
   └──────────────────────┘                                    │
            │                                                  │
            ▼                                                  │
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ INSERT INTO rag_query_log (query_text, chunks_returned, similarity...)  │
   └──────────────────────────────────────────────────────────────────────────┘
            │                                                  │
            └──────────────────────┬───────────────────────────┘
                                   │
                                   ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │                       MONTAGEM DO PROMPT FINAL                           │
   │                                                                          │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ SYSTEM PROMPT (v1.0.0) ─ identidade, horário, diretrizes        │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   │                              +                                           │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ CONTEXTO RAG (se houver match) ─ chunks de política             │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   │                              +                                           │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ DADOS DO BANCO ─ produtos encontrados, estoque, preços          │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   │                              +                                           │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ HISTÓRICO ─ mensagens anteriores desta sessão                   │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   │                              +                                           │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ MENSAGEM DO CLIENTE ─ "Vocês têm violão Yamaha?"                │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   └──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │     LLM API      │
                        │   (GPT-4, etc)   │
                        └──────────────────┘
                                   │
                                   ▼
4. AGENTE RESPONDE
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ INSERT INTO chat_messages (                                              │
   │   session_id,                                                            │
   │   role = 'assistant',                                                    │
   │   content = "Temos 14 unidades do Yamaha F310 por R$ 699,90...",        │
   │   model_used = 'gpt-4',                                                  │
   │   tokens_input = 1850,                                                   │
   │   tokens_output = 120,                                                   │
   │   response_time_ms = 2340,                                               │
   │   sources_consulted = '{"tables": ["products"], "chunks": []}'           │
   │ )                                                                        │
   └──────────────────────────────────────────────────────────────────────────┘

5. IDENTIFICAÇÃO DO CLIENTE (quando informa email/telefone)
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ SELECT customer_id FROM customers WHERE email = 'cliente@email.com'      │
   │                                                                          │
   │ Se encontrar → UPDATE chat_sessions SET customer_id = X                  │
   │                                                                          │
   │ A partir daqui, agente pode consultar:                                   │
   │   - v_customer_orders_summary (histórico de compras)                     │
   │   - v_order_details (detalhes de pedidos específicos)                    │
   └──────────────────────────────────────────────────────────────────────────┘

6. AVALIAÇÃO (posterior, por humano ou sistema)
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ UPDATE chat_messages SET rating='positive', rating_feedback='...'        │
   │ UPDATE agent_prompts SET times_used = times_used + 1                     │
   └──────────────────────────────────────────────────────────────────────────┘

7. ENCERRAMENTO
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ UPDATE chat_sessions SET status='ended', ended_at=now()                  │
   └──────────────────────────────────────────────────────────────────────────┘
```

### Resumo: O que cada etapa ESCREVE

| Etapa | Tabela | Campos Preenchidos |
|-------|--------|-------------------|
| Início sessão | `chat_sessions` | session_id, started_at, status, channel |
| Mensagem user | `chat_messages` | role=user, content, created_at |
| Busca RAG | `rag_query_log` | query_text, chunks_returned, similarity, search_time_ms |
| Resposta | `chat_messages` | role=assistant, content, model_used, tokens_*, response_time_ms, sources_consulted |
| Identificação | `chat_sessions` | customer_id (UPDATE) |
| Avaliação | `chat_messages` | rating, rating_feedback, rated_at (UPDATE) |
| Encerramento | `chat_sessions` | status=ended, ended_at (UPDATE) |

---

## Estrutura do Projeto

```
artefact/
├── data/                                    # CSVs de origem (já importados ao Supabase)
│   ├── desafio_tecnico_ai_eng - categories.csv
│   ├── desafio_tecnico_ai_eng - customers.csv
│   ├── desafio_tecnico_ai_eng - products.csv
│   ├── desafio_tecnico_ai_eng - promotions.csv
│   ├── desafio_tecnico_ai_eng - orders.csv
│   ├── desafio_tecnico_ai_eng - order_items.csv
│   └── políticas_da_loja.pdf               # Documento fonte do RAG
├── prompts/
│   ├── system_prompt_v1.0.0.md             # Prompt fixo do agente (versão atual)
│   └── rag_chunks_definition.md            # Definição documentada dos 14 chunks RAG
├── scripts/
│   ├── mcp-postgrest.cjs                   # Wrapper do MCP (lê .env e inicia o servidor PostgREST)
│   └── seed_rag.py                         # Gera embeddings e popula agent_prompts + rag_chunks
├── supabase/
│   ├── config.toml
│   └── migrations/
│       ├── 20250901220000_initial_schema.sql      # Tabelas de e-commerce
│       ├── 20250901230000_chat_agent_tables.sql   # Tabelas do agente
│       └── 20250902233900_rag_and_prompts.sql     # Tabelas agent_prompts, rag_chunks, rag_query_log
├── .cursor/
│   └── mcp.json                            # Config do MCP Supabase (nível do projeto)
├── .env                                    # Credenciais locais (não versionado)
├── .env.example                            # Modelo de credenciais (Supabase + OpenAI)
├── requirements.txt                        # Dependências Python (httpx)
└── README.md
```

---

## Integração Supabase + GitHub

1. **Project Settings → Integrations → GitHub**
2. **Working directory:** `.`
3. **Production branch:** `main`
4. Migrations aplicadas automaticamente a cada push

## MCP Supabase (Cursor)

O projeto usa um MCP local (`todos`) para consultar e alimentar o banco diretamente pelo Cursor via PostgREST.

1. Copie `.env.example` para `.env` e preencha:
   - `SUPABASE_REST_URL` → URL do projeto + `/rest/v1`
   - `SUPABASE_KEY` → `service_role` secret (Project Settings → API)
2. Recarregue o Cursor (`Ctrl+Shift+P` → Reload Window)
3. Confirme em **Cursor Settings → MCP** que o servidor `todos` está conectado

O wrapper `scripts/mcp-postgrest.cjs` lê o `.env` e inicia `@supabase/mcp-server-postgrest`, contornando a limitação do Cursor de não interpolar variáveis de ambiente diretamente nos `args` do `mcp.json`.

---

## Status

- [x] Migrations aplicadas no Supabase
- [x] Dados dos CSVs importados (categories, customers, products, promotions, orders, order_items)
- [x] Estrutura RAG criada (`agent_prompts`, `rag_chunks`, `rag_query_log`, função `match_chunks`)
- [x] System prompt v1.0.0 e 14 chunks de política definidos e documentados
- [x] Embeddings gerados e dados populados via `seed_rag.py`
- [ ] Implementar lógica do agente (`feature/agent`)
- [ ] Criar endpoint da API
- [ ] Criar frontend de chat
- [ ] Dashboard de métricas e acompanhamento
