# Artefact — Agente Conversacional para E-commerce de Instrumentos Musicais

Agente de atendimento da **Empório da Música** (Campo Grande/MS): responde clientes com persona da loja, consulta produtos/pedidos no banco e políticas via RAG, e oferece painel admin para a equipe acompanhar conversas, métricas, promoções e o modelo de IA.

## Como ver o projeto

Demo online (frontend na Vercel):

**https://emporio-five.vercel.app/**

| Visão | URL |
|-------|-----|
| Chat do cliente | [https://emporio-five.vercel.app/](https://emporio-five.vercel.app/) |
| Admin — conversas | [https://emporio-five.vercel.app/admin](https://emporio-five.vercel.app/admin) |
| Admin — dashboard | [https://emporio-five.vercel.app/admin/dashboard](https://emporio-five.vercel.app/admin/dashboard) |
| Admin — promoções | [https://emporio-five.vercel.app/admin/promocoes](https://emporio-five.vercel.app/admin/promocoes) |
| Admin — modelo IA | [https://emporio-five.vercel.app/admin/modelo](https://emporio-five.vercel.app/admin/modelo) |

## Índice

1. [Visão geral](#visão-geral-do-projeto)
2. [Entregáveis do desafio](#entregáveis-do-desafio)
3. [Decisões técnicas](#decisões-técnicas)
4. [Arquitetura](#arquitetura-do-sistema)
5. [Banco de dados](#estrutura-do-banco-de-dados)
6. [RAG e versionamento de prompts](#arquitetura-rag-e-versionamento-de-prompts)
7. [Fluxo ponta a ponta](#fluxo-de-execução-do-agente-ponta-a-ponta)
8. [Estrutura do código](#estrutura-do-projeto)
9. [Como rodar](#como-rodar-o-projeto)
10. [Deploy](#deploy-vercel--render)
11. [Exemplos de interação](#exemplos-de-interação)
12. [Limitações e próximos passos](#limitações-conhecidas-e-próximos-passos)
13. [Uso de IA no desenvolvimento](#uso-de-ia-no-desenvolvimento)
14. [API REST](#api-rest-fastapi)

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
| Preços e promoções | `products`, `promotions` (`is_active`) | "Qual o preço do ukulele Kala?" |
| Status de pedido | `orders`, `order_items` | "Onde está meu pedido #15?" |
| Identificação do cliente | `customers` + campo WhatsApp no chat | Telefone/e-mail no header ou na mensagem |
| Políticas da loja | `rag_chunks` (RAG) | "Qual o prazo de devolução?" |
| Formas de pagamento | Políticas + ENUMs | "Vocês parcelam em quantas vezes?" |
| Horário de atendimento | Relógio local (Campo Grande) + prompt | Avisa retorno se fora do expediente |
| Troca de modelo LLM | Admin → Modelo IA (`gpt-4o` padrão) | Equipe escolhe o modelo sem redeploy |

---

## Entregáveis do Desafio

Mapeamento direto do [desafio técnico](desafio_tecnico_ai_eng_artefact.md) → o que este repositório entrega:

| Pedido | Entrega |
|--------|---------|
| Agente em Python com persona da loja | `agent/` + prompt versionado **v2.1.2** (playbook de condução) |
| Consultar dados (estoque, preço, pedido) | PostgREST → `products`, `promotions`, `orders`, `customers` |
| Consultar políticas (troca, frete, pagamento) | RAG sobre `data/políticas_da_loja.pdf` → `rag_chunks` + `match_chunks` |
| Fora de escopo | Prompt + exemplos (`examples/05_fora_do_escopo.md`) |
| README com setup, decisões, limitações e uso de IA | Este arquivo |
| 3–5 conversas de exemplo (uma não trivial) | `examples/01` … `05` (devolução = não trivial) |
| Histórico de commits real | Repositório GitHub público |

---

## Decisões Técnicas

Justificativas pedidas no enunciado (detalhamento do RAG nas [7 decisões](#arquitetura-rag-e-versionamento-de-prompts) abaixo).

| Decisão | Escolha | Por quê |
|---------|---------|---------|
| **Abordagem do agente** | Híbrido: **intent leve + SQL/PostgREST + RAG** | Dados operacionais (preço/estoque/pedido) precisam ser factuais do banco; políticas são texto semântico — RAG. Evita “agente SQL livre” inventando queries e evita colocar o PDF inteiro no prompt. |
| **Modelo / provedor** | OpenAI **`gpt-4o`** (padrão); admin pode trocar para mini / 4.1 | Bom equilíbrio qualidade × custo para atendimento. Mini fica disponível se quiser economizar (tom mais seco). Embeddings: `text-embedding-3-small`. |
| **Interface** | **UI web** (chat WhatsApp-like) + **API FastAPI** + CLI opcional | Avaliador e “equipe da loja” usam o mesmo produto; API documentada em `/docs`. |
| **Histórico** | `chat_sessions` + `chat_messages` no Supabase | Continuidade na sessão, métricas (tokens, latência, rating) e painel admin. |
| **Tratamento dos dados** | CSVs → Supabase; PDF → chunks curados + embeddings | Domínio pequeno e estável: curadoria manual dos 14 chunks supera chunker genérico neste caso. |
| **Persistência do prompt / modelo** | `agent_prompts` (versão ativa + `runtime_settings`) | Prompt versionado com rollback; modelo LLM muda no admin sem redeploy. |

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
                              │ sources_consulted   │
                              └─────────────────────┘

┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│   agent_prompts     │       │     rag_chunks      │       │   rag_query_log     │
├─────────────────────┤       ├─────────────────────┤       ├─────────────────────┤
│ prompt_id PK (UUID) │       │ chunk_id PK (UUID)  │       │ log_id PK           │
│ name                │       │ content             │       │ query_text          │
│ version             │       │ embedding (vector)  │       │ chunks_returned     │
│ content             │       │ category            │       │ top/avg similarity  │
│ is_active           │       │ keywords[]          │       │ session_id FK (null)│
│ times_used          │       │ is_active           │       │ was_relevant        │
└─────────────────────┘       └─────────────────────┘       └─────────────────────┘
  ↑ system_prompt + runtime_settings (modelo LLM)
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
| `chat_messages.session_id` | `chat_sessions.session_id` | N:1 | Mensagem pertence a uma sessão (cascade delete) |
| `rag_query_log.session_id` | `chat_sessions.session_id` | N:1 | Log RAG opcionalmente ligado à sessão (set null) |

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
| `model_used` | text | Modelo de IA (ex.: `gpt-4o`) |
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

---

### Domínio: RAG e Prompts

#### `agent_prompts`
Prompts versionados do agente. Também guarda config runtime (`name = runtime_settings`, JSON com `llm_model`).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `prompt_id` | uuid | PK |
| `name` | text | Ex.: `system_prompt`, `runtime_settings` |
| `version` | text | Semver (ex.: `2.1.2`) |
| `content` | text | Texto do prompt ou JSON de settings |
| `is_active` | boolean | Apenas um ativo por `name` (trigger) |
| `times_used` | integer | Contador de uso |
| `avg_accuracy` | numeric | Acurácia agregada (opcional) |

#### `rag_chunks`
Trechos de política com embedding para busca semântica.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `chunk_id` | uuid | PK |
| `content` | text | Texto do chunk |
| `embedding` | vector(1536) | Embedding OpenAI |
| `category` | text | `pagamento`, `troca`, `frete`, etc. |
| `keywords` | text[] | Termos de apoio à busca |
| `is_active` | boolean | Soft-delete |

#### `rag_query_log`
Auditoria de cada busca RAG (similaridade, tempo, chunks).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `log_id` | uuid/bigint | PK |
| `query_text` | text | Pergunta / query embutida |
| `chunks_returned` | jsonb/array | IDs/conteúdos retornados |
| `top_similarity` / `avg_similarity` | float | Scores |
| `search_time_ms` | integer | Latência da busca |
| `session_id` | uuid | FK opcional → `chat_sessions` |
| `was_relevant` | boolean | Avaliação manual posterior |

> Migration `20250903004500_remove_knowledge_sources.sql` remove a tabela legada `knowledge_sources` (substituída por `rag_chunks`).

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

### Controle do Agente / RAG

| View | Descrição |
|------|-----------|
| `v_chat_sessions_summary` | Sessões com métricas (duração, mensagens, tokens) |
| `v_chat_conversation_history` | Histórico formatado para frontend |
| `v_customer_chat_history` | Interações por cliente |
| `v_agent_accuracy_metrics` | **Acurácia diária do agente** |
| `v_low_rated_responses` | Respostas negativas para revisão |
| `v_active_prompt` | Prompt(s) ativo(s) para o agente |
| `v_rag_performance` | Taxa de relevância / similaridade do RAG |
| `v_chunks_by_category` | Resumo dos chunks por categoria |

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
   │ → Carrega o prompt ativo (ex.: v2.1.2 — playbook de condução)            │
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
   │  │ SYSTEM PROMPT (ativo) ─ identidade, workflow, tom, exemplos         │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   │                              +                                           │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ STATUS DO ATENDIMENTO + DADOS DO SISTEMA (mensagem system extra)  │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   │                              +                                           │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ CONTEXTO RAG (se houver match) ─ chunks de política             │     │
   │  └─────────────────────────────────────────────────────────────────┘     │
   │                              +                                           │
   │  ┌─────────────────────────────────────────────────────────────────┐     │
   │  │ DADOS DO BANCO ─ produtos, estoque, preços (com promo ativa)    │     │
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
                        │   OpenAI Chat    │
                        │  (padrão gpt-4o) │
                        └──────────────────┘
                                   │
                                   ▼
4. AGENTE RESPONDE
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ INSERT INTO chat_messages (                                              │
   │   session_id,                                                            │
   │   role = 'assistant',                                                    │
   │   content = "Temos 14 unidades do Yamaha F310 por R$ 699,90...",        │
   │   model_used = 'gpt-4o',                                                 │
   │   tokens_input = 1850,                                                   │
   │   tokens_output = 120,                                                   │
   │   response_time_ms = 2340,                                               │
   │   sources_consulted = '{"tables": ["products"], "chunks": []}'           │
   │ )                                                                        │
   └──────────────────────────────────────────────────────────────────────────┘

5. IDENTIFICAÇÃO DO CLIENTE (telefone/e-mail no header do chat ou na mensagem)
   ┌──────────────────────────────────────────────────────────────────────────┐
   │ POST /sessions/{id}/identify  OU  extração do contato na mensagem        │
   │ → Busca em customers; vincula customer_id à sessão                       │
   │ → Agente passa a usar o nome do cliente                                  │
   │ → Pode consultar v_customer_orders_summary / v_order_details             │
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
├── agent/                                   # Núcleo do agente (Python)
│   ├── __init__.py                         # Exporta Agent
│   ├── config.py                           # Env + Config (LLM_MODEL padrão gpt-4o)
│   ├── database.py                         # PostgREST (sessões, produtos, prompts…)
│   ├── embeddings.py                       # Embeddings OpenAI
│   ├── rag.py                              # Busca semântica match_chunks
│   ├── llm.py                              # Chat Completions (modelo por request)
│   ├── runtime_settings.py                 # Modelo LLM ativo (admin + cache)
│   ├── chat.py                             # Orquestração: intent → contexto → LLM
│   └── main.py                             # CLI de teste
├── api/                                     # API REST
│   ├── schemas.py                          # Pydantic
│   └── main.py                             # FastAPI (sessions, chat, admin)
├── frontend/                                # Vite + React + Tailwind
│   ├── public/favicon.svg                  # Nota musical
│   ├── vercel.json                         # SPA rewrites
│   └── src/
│       ├── components/
│       │   ├── ChatClient.tsx              # Chat cliente (+ WhatsApp no header)
│       │   ├── AdminConversations.tsx      # Conversas + rating
│       │   ├── AdminDashboard.tsx          # Métricas
│       │   ├── AdminPromotions.tsx         # Toggle is_active
│       │   ├── AdminSettings.tsx           # Seletor de modelo OpenAI
│       │   └── AdminSidebar.tsx
│       ├── layouts/AdminLayout.tsx
│       ├── api.ts                          # Cliente HTTP (VITE_API_URL)
│       └── App.tsx                         # Rotas /, /admin, …/modelo
├── data/                                    # CSVs + políticas_da_loja.pdf
├── prompts/
│   ├── system_prompt_v2.1.2.md             # Versão ativa (seed)
│   ├── system_prompt_v*.md                 # Histórico de versões
│   └── rag_chunks_definition.md            # Curadoria dos 14 chunks
├── examples/                                # 5 conversas de demonstração
├── scripts/
│   ├── seed_rag.py                         # Popula prompts + embeddings
│   ├── validate_agent_round.py             # Smoke de validação RAG+DB
│   └── mcp-postgrest.cjs                   # MCP Cursor → PostgREST
├── supabase/migrations/
│   ├── 20250901220000_initial_schema.sql
│   ├── 20250901230000_chat_agent_tables.sql
│   ├── 20250902233900_rag_and_prompts.sql
│   └── 20250903004500_remove_knowledge_sources.sql
├── Procfile / render.yaml / runtime.txt    # Deploy API (Render, Python 3.12)
├── .env.example                            # SUPABASE_*, OPENAI_*, LLM_MODEL, FRONTEND_ORIGIN
├── requirements.txt
└── README.md
```

### Organização do código (camadas)

| Camada | Pasta | Responsabilidade |
|--------|-------|------------------|
| Orquestração | `agent/chat.py` | Intent, contexto, montagem de mensagens, limpeza da resposta |
| Integrações | `agent/database.py`, `llm.py`, `rag.py`, `embeddings.py` | I/O externo isolado |
| Config runtime | `agent/config.py`, `runtime_settings.py` | Env + modelo escolhido no admin |
| Transporte | `api/` | HTTP fino; regras de negócio ficam no `agent/` |
| UI | `frontend/src` | Chat cliente vs painel admin em rotas separadas |

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

## Como Rodar o Projeto

### Pré-requisitos

- Python **3.12** (pin em `runtime.txt`; 3.11+ costuma funcionar localmente)
- Node.js 18+ (frontend)
- Conta no [Supabase](https://supabase.com) com o projeto criado e as migrations aplicadas
- Chave de API da [OpenAI](https://platform.openai.com)

### 1. Clone e instale dependências

```bash
git clone https://github.com/gustavopoffo/artefact.git
cd artefact
pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais:

```env
SUPABASE_REST_URL=https://<projeto>.supabase.co/rest/v1
SUPABASE_KEY=<service_role_secret>
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
FRONTEND_ORIGIN=*
```

> **SUPABASE_KEY:** use a `service_role` secret (Project Settings → API → Project API Keys). Nunca a `anon public`.  
> **LLM_MODEL:** padrão `gpt-4o`. Também pode ser alterado em **Admin → Modelo IA** (persiste em `agent_prompts` / `runtime_settings`).

### 3. Popule o banco com os dados de RAG e prompts

```bash
python scripts/seed_rag.py
```

Este script:
- Gera embeddings para os 14 chunks de política da loja via `text-embedding-3-small`
- Insere os chunks na tabela `rag_chunks` (é idempotente — ignora chunks já existentes)
- Insere/ativa o `system_prompt` da versão definida em `scripts/seed_rag.py` (hoje **v2.1.2**)

> **Os dados de e-commerce** (produtos, clientes, pedidos) já foram importados dos CSVs para o Supabase e estão no banco. Nenhuma ação adicional é necessária.

Opcional — validar uma rodada do agente (RAG + DB):

```bash
python scripts/validate_agent_round.py
```

### 4. Rode a API e o frontend

**Terminal 1 — API:**

```bash
python -m uvicorn api.main:app --reload --port 8000
```

> No Windows, prefira `python -m uvicorn` — o comando `uvicorn` sozinho pode não estar no PATH.

**Terminal 2 — Frontend:**

```bash
cd frontend
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

| URL | Visão |
|-----|--------|
| http://localhost:5173/ | Chat do cliente (estilo WhatsApp) + WhatsApp opcional no header |
| http://localhost:5173/admin | Conversas (visão empresa) + avaliação 👍/👎 |
| http://localhost:5173/admin/dashboard | Dashboard de métricas |
| http://localhost:5173/admin/promocoes | Ativar/desativar promoções (`promotions.is_active`) |
| http://localhost:5173/admin/modelo | Selecionar modelo OpenAI (`gpt-4o` padrão) |
| http://localhost:8000/docs | Swagger da API |

No chat do cliente, o ícone de engrenagem abre o painel admin. O campo de WhatsApp no header identifica o cliente na base e personaliza o atendimento pelo nome.

**Via CLI (opcional):**

```bash
python -m agent.main
```

**Via Python:**

```python
from agent import Agent

agent = Agent(channel="web")
response = agent.chat("Vocês têm violão Yamaha?")

print(response.content)
print(f"Tokens: {response.tokens_input} + {response.tokens_output}")
print(f"Tempo: {response.response_time_ms}ms")
print(f"RAG chunks usados: {response.rag_chunks_used}")
print(f"Cliente identificado: {response.customer_identified}")
```

---

## Deploy (Vercel + Render)

Arquitetura em produção:

```
Browser → Vercel (frontend Vite/React)
              │  VITE_API_URL
              ▼
         Render (FastAPI / uvicorn)
              ├── Supabase (PostgREST)
              └── OpenAI (embeddings + chat)
```

### 1. API no Render

1. Conta em [render.com](https://render.com) → **New → Web Service**
2. Conecte o repositório GitHub (`gustavopoffo/artefact`)
3. Configuração sugerida:
   - **Root Directory:** (raiz do repo)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
4. Variáveis de ambiente (Environment):

| Variável | Valor |
|----------|--------|
| `SUPABASE_REST_URL` | `https://<projeto>.supabase.co/rest/v1` |
| `SUPABASE_KEY` | `service_role` secret |
| `OPENAI_API_KEY` | chave OpenAI |
| `LLM_MODEL` | `gpt-4o` (opcional; admin também altera) |
| `FRONTEND_ORIGIN` | URL da Vercel (ex. `https://emporio-five.vercel.app`) — ou `*` no início |

5. Após o deploy, teste: `https://<seu-servico>.onrender.com/health`

> **Cold start:** no plano free o serviço “dorme” após inatividade. A primeira request pode demorar ~30–60s. Chamadas ao chat já usam timeout de 60s na OpenAI.

Opcional: use o blueprint [`render.yaml`](render.yaml) (New → Blueprint).

### 2. Frontend na Vercel

1. Conta em [vercel.com](https://vercel.com) → **Add New Project** → importe o mesmo repo
2. Configuração:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build` (padrão)
   - **Output Directory:** `dist` (padrão)
3. Environment Variable:

| Variável | Valor |
|----------|--------|
| `VITE_API_URL` | URL pública do Render **sem** barra no final (ex. `https://emporio-musica-api.onrender.com`) |

4. Deploy. O [`frontend/vercel.json`](frontend/vercel.json) faz rewrite SPA para o React Router (`/admin`, `/admin/promocoes`, `/admin/modelo`, etc.).

5. Atualize no Render a variável `FRONTEND_ORIGIN` com a URL final da Vercel e faça redeploy da API (se não estiver usando `*`).

### 3. Smoke test em produção

1. `GET /health` na API → `{"status":"ok",...}`
2. Abrir o site na Vercel → enviar “oi” no chat
3. Admin → Promoções → ativar/desativar um item
4. Admin → Modelo IA → confirmar `gpt-4o` (ou trocar e testar uma mensagem)
5. Perguntar o preço de um produto em promoção e conferir o de/por

### Variáveis locais (desenvolvimento)

- Raiz: copie [`.env.example`](.env.example) → `.env` (Supabase + OpenAI + `LLM_MODEL` + `FRONTEND_ORIGIN`)
- Front: copie [`frontend/.env.example`](frontend/.env.example) → `frontend/.env` com `VITE_API_URL=http://localhost:8000`

---

## Exemplos de Interação

A pasta `examples/` contém 5 conversas reais geradas com o agente em funcionamento, cobrindo os principais cenários:

| Arquivo | Cenário |
|---------|---------|
| `01_catalogo_violoes.md` | Consulta ao catálogo — violões disponíveis até R$1.000 |
| `02_politica_devolucao.md` | Política de devolução — situação não trivial (compra há 10 dias) |
| `03_preco_produto_especifico.md` | Consulta de preço de produto específico + verificação de promoção |
| `04_status_pedido.md` | Identificação do cliente por email + pedido sem cadastro |
| `05_fora_do_escopo.md` | Perguntas fora do escopo da loja (apps de música, aulas) |

---

## Limitações Conhecidas e Próximos Passos

### Limitações atuais

| Limitação | Impacto | O que faria com mais tempo |
|-----------|---------|---------------------------|
| **Identificação de cliente por telefone/e-mail** | Campo no header do chat + texto na mensagem; sem login | Integrar com WhatsApp Business API ou sistema de autenticação |
| **RAG com apenas 14 chunks fixos** | Novos documentos exigem curadoria manual | Pipeline automático com Docling (OCR) + chunker semântico para escalar |
| **Busca de produto sem acento nativo** | Contorna com mapeamento em Python; ideal seria extensão `unaccent` no PostgreSQL | Habilitar extensão `unaccent` via migration e usar `ilike` nos dados normalizados |
| **Sem memória de longo prazo entre sessões** | Agente não "lembra" preferências de sessões anteriores do mesmo cliente | Salvar preferências do cliente em `customers.metadata` e carregar na próxima sessão |
| **Apenas 1 provedor LLM (OpenAI)** | Dependência de um único fornecedor (modelo trocável no admin) | Abstrair o LLM para suporte Anthropic/Gemini como fallback |
| **Modelo de avaliação reativo** | Rating só coletado depois da resposta, por humano no admin | Sistema automático de avaliação usando LLM como juiz (LLM-as-a-judge) |
| **Latência da OpenAI variável** | Em alguns momentos a chamada LLM pode demorar dezenas de segundos | Cache de prompt, streaming e monitoramento de rede |

### O que faria com mais tempo

1. **Avaliação automática de respostas** — usar um segundo LLM para avaliar se a resposta foi factualmente correta dado o contexto
2. **Curadoria iterativa do prompt** — comparar versões do prompt objetivamente com base em ratings reais
3. **Escalabilidade do RAG** — novos documentos via pipeline automatizado com Docling e chunker semântico
4. **Auth no painel admin** — proteger `/admin` com login
5. **Integração WhatsApp Business** — canal real de atendimento

---

## Uso de IA no Desenvolvimento

Este projeto foi desenvolvido com o auxílio do [Cursor IDE](https://cursor.com) com Claude Sonnet 4.5 como assistente de código.

### Como foi usado

| Etapa | Uso do Cursor/Claude |
|-------|----------------------|
| **Modelagem do banco** | Revisão crítica das tabelas, sugestão de constraints e índices, identificação de relacionamentos faltantes |
| **Arquitetura RAG** | Análise do PDF seção a seção, decisão sobre o que vai para RAG vs. system prompt, curadoria dos 14 chunks |
| **Implementação do agente** | Geração dos módulos `database.py`, `rag.py`, `llm.py`, `chat.py` com pair programming iterativo |
| **Debug** | Identificação de bugs como: `ilike` sem acento, pattern regex capturando parte errada da mensagem, `message_id` sendo logado antes de existir |
| **Documentação** | Estruturação do README com justificativas técnicas, diagramas ASCII, tabelas de decisão |

### Workflow adotado

O fluxo foi sempre **humano no loop de decisão**: o assistente propunha soluções, o desenvolvedor avaliava a lógica, identificava gaps e redirecionava. Nenhuma decisão arquitetural foi delegada inteiramente ao modelo — todas foram revisadas, questionadas e frequentemente modificadas antes de implementar.

Exemplo concreto: o assistente inicialmente sugeriu usar Docling para OCR do PDF. O desenvolvedor questionou se fazia sentido rodar OCR em um PDF com texto nativo — e a decisão final foi extrair manualmente, com justificativa documentada na "Decisão 2" acima.

---

## Status

- [x] Migrations aplicadas no Supabase
- [x] Dados dos CSVs importados (categories, customers, products, promotions, orders, order_items)
- [x] Estrutura RAG criada (`agent_prompts`, `rag_chunks`, `rag_query_log`, função `match_chunks`)
- [x] System prompt versionado (ativa: **v2.1.2** — playbook de condução) e 14 chunks de política
- [x] Embeddings gerados e dados populados via `seed_rag.py`
- [x] Lógica do agente implementada (`agent/`)
- [x] Exemplos de interação documentados em `examples/`
- [x] Endpoint REST (FastAPI)
- [x] Frontend de chat (visão cliente) + identificação por WhatsApp no header
- [x] Painel admin de conversas + avaliação de acurácia
- [x] Dashboard de métricas
- [x] Admin de promoções (ativar/desativar `is_active` e refletir preço no chat)
- [x] Admin de modelo IA (`gpt-4o` padrão; persistido em `runtime_settings`)
- [x] Deploy em produção (Vercel front + Render API) — demo: https://emporio-five.vercel.app/

## API REST (FastAPI)

### Subir o servidor

```bash
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000
```

Docs interativas: http://localhost:8000/docs

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check |
| `POST` | `/sessions` | Cria sessão (`{"channel": "web"}`) |
| `GET` | `/sessions/{id}` | Dados da sessão |
| `POST` | `/sessions/{id}/end` | Encerra sessão |
| `POST` | `/sessions/{id}/identify` | Identifica cliente por telefone e vincula à sessão |
| `POST` | `/sessions/{id}/messages` | Envia mensagem e recebe resposta do agente |
| `GET` | `/sessions/{id}/messages` | Histórico da conversa |
| `GET` | `/admin/sessions` | Lista sessões com resumo (contagem, última msg) |
| `GET` | `/admin/metrics` | Métricas agregadas do dashboard |
| `GET` | `/admin/promotions` | Lista promoções com preço original/descontado |
| `PATCH` | `/admin/promotions/{id}` | Ativa/desativa promoção (`{"is_active": true}`) |
| `GET` | `/admin/settings` | Modelo LLM ativo + lista de opções |
| `PATCH` | `/admin/settings` | Atualiza modelo (`{"llm_model": "gpt-4o"}`) |
| `PATCH` | `/admin/messages/{id}/rating` | Avalia resposta (`positive` / `negative` / `neutral`) |

### Avaliação de acurácia

No painel **Admin → Conversas**, cada resposta do agente tem botões 👍 / 👎.  
Isso grava `chat_messages.rating` e alimenta o gráfico de acurácia em **Admin → Dashboard**.

### Promoções

Em **Admin → Promoções**, o dono da loja ativa ou desativa descontos. O agente consulta `v_products_with_active_promotion` e apresenta o preço promocional (de/por) quando `is_active = true`.

### Modelo de IA

Em **Admin → Modelo IA**, a equipe escolhe o modelo OpenAI. O valor fica em `agent_prompts` (`name = runtime_settings`) e vale para as próximas mensagens sem redeploy.

### Exemplo rápido

```bash
# 1. Criar sessão
curl -X POST http://localhost:8000/sessions -H "Content-Type: application/json" -d "{\"channel\":\"web\"}"

# 2. Enviar mensagem (substitua SESSION_ID)
curl -X POST http://localhost:8000/sessions/SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Vocês têm violão Yamaha?\"}"
```
