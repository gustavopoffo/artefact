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
│   └── políticas_da_loja.pdf               # Documento para RAG
├── scripts/
│   └── mcp-postgrest.cjs                   # Wrapper do MCP (lê .env e inicia o servidor PostgREST)
├── supabase/
│   ├── config.toml
│   └── migrations/
│       ├── 20250901220000_initial_schema.sql      # Tabelas de e-commerce
│       └── 20250901230000_chat_agent_tables.sql   # Tabelas do agente
├── .cursor/
│   └── mcp.json                            # Config do MCP Supabase (nível do projeto)
├── .env                                    # Credenciais locais (não versionado)
├── .env.example                            # Modelo de credenciais
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
- [ ] Configurar embeddings do PDF de políticas
- [ ] Implementar endpoint da API do agente
- [ ] Criar frontend de chat
- [ ] Dashboard de métricas e acompanhamento
