# Artefact — E-commerce de Instrumentos Musicais

Sistema de banco de dados para uma loja de instrumentos musicais no Mato Grosso do Sul, projetado para permitir consultas inteligentes por IA.

## Proposta de Solução

### Objetivo

Criar uma estrutura de banco de dados que permita a uma **IA realizar consultas SQL de forma inteligente** para responder perguntas sobre o negócio. Para isso, o schema foi desenhado com:

1. **Relacionamentos explícitos via Foreign Keys** — A IA consegue entender como as tabelas se conectam
2. **Tipos enumerados (ENUMs)** — Valores válidos são auto-documentados no schema
3. **Comentários em todas as tabelas e colunas** — Contexto semântico para a IA
4. **Constraints de validação** — Regras de negócio embutidas no banco
5. **Views pré-definidas** — Consultas complexas já otimizadas para perguntas comuns

### Por que essa abordagem?

Quando uma IA precisa gerar SQL, ela analisa o schema do banco para entender:
- Quais tabelas existem e o que representam
- Como as tabelas se relacionam (JOINs necessários)
- Quais valores são válidos para cada campo
- Quais índices otimizam as consultas

Um schema bem documentado reduz erros de interpretação e permite respostas mais precisas.

---

## Diagrama de Relacionamento (ERD)

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
                     │                              │ specs (JSONB)   │  │
                     │ 1:N                          │ created_at      │  │
                     │                              └─────────────────┘  │
                     │                                                   │
┌────────────────────┴──┐       ┌─────────────────┐                      │
│       orders          │       │   order_items   │                      │
├───────────────────────┤       ├─────────────────┤                      │
│ order_id PK           │───────│ order_item_id PK│                      │
│ customer_id FK        │  1:N  │ order_id FK     │                      │
│ order_date            │       │ product_id FK   │──────────────────────┘
│ status                │       │ quantity        │           N:1
│ total_brl             │       └─────────────────┘
│ payment_method        │
│ tracking_code         │
│ estimated_delivery    │
│ notes                 │
└───────────────────────┘
```

### Relacionamentos

| Origem | Destino | Cardinalidade | Descrição |
|--------|---------|---------------|-----------|
| `products.category_id` | `categories.category_id` | N:1 | Cada produto pertence a uma categoria |
| `promotions.product_id` | `products.product_id` | N:1 | Cada promoção aplica-se a um produto |
| `orders.customer_id` | `customers.customer_id` | N:1 | Cada pedido pertence a um cliente |
| `order_items.order_id` | `orders.order_id` | N:1 | Cada item pertence a um pedido |
| `order_items.product_id` | `products.product_id` | N:1 | Cada item referencia um produto |

A tabela `order_items` funciona como **tabela associativa** entre `orders` e `products`, permitindo que um pedido contenha múltiplos produtos (relação N:N resolvida).

---

## Estrutura do Projeto

```
artefact/
├── data/                           # CSVs de origem
│   ├── desafio_tecnico_ai_eng - categories.csv
│   ├── desafio_tecnico_ai_eng - customers.csv
│   ├── desafio_tecnico_ai_eng - products.csv
│   ├── desafio_tecnico_ai_eng - promotions.csv
│   ├── desafio_tecnico_ai_eng - orders.csv
│   └── desafio_tecnico_ai_eng - order_items.csv
├── supabase/
│   ├── config.toml                 # Configuração do projeto Supabase
│   └── migrations/
│       └── 20250901220000_initial_schema.sql  # Schema completo
└── README.md
```

---

## Tabelas

### `categories`
Categorias de instrumentos musicais vendidos na loja.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `category_id` | integer | PK — Identificador único |
| `name` | text | Nome da categoria (único) |
| `description` | text | Descrição detalhada |

**Categorias existentes:** Guitarras, Baixos, Baterias e Percussão, Teclados e Pianos, Violões, Instrumentos de Sopro (Madeiras), Instrumentos de Sopro (Metais), Cordas Orquestrais, Ukuleles.

---

### `customers`
Clientes da loja, todos localizados no Mato Grosso do Sul.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `customer_id` | integer | PK — Identificador único |
| `name` | text | Nome completo |
| `phone` | text | Telefone (67) XXXXX-XXXX |
| `email` | text | E-mail (único) |
| `city` | text | Cidade no MS |

**Cidades:** Campo Grande, Dourados, Três Lagoas, Corumbá, Ponta Porã.

---

### `products`
Instrumentos musicais à venda.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `product_id` | integer | PK — Identificador único |
| `name` | text | Nome comercial (marca + modelo) |
| `price_brl` | numeric(10,2) | Preço em Reais |
| `category_id` | integer | FK → `categories` |
| `description` | text | Descrição detalhada |
| `stock_quantity` | integer | Quantidade em estoque |
| `status` | product_status | `active`, `discontinued`, `coming_soon` |
| `specs` | jsonb | Especificações técnicas |
| `created_at` | date | Data de cadastro |

**Campo `specs` (JSONB):** Contém atributos variáveis por tipo de instrumento:
- Violões/Guitarras: `top`, `back_sides`, `neck`, `strings`, `scale`, `electronics`, `color`
- Baterias: `shells`, `pieces`, `hardware`, `color`
- Teclados: `keys`, `type`, `polyphony`, `color`

---

### `promotions`
Promoções e descontos aplicáveis a produtos.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `promotion_id` | integer | PK — Identificador único |
| `product_id` | integer | FK → `products` |
| `discount_percent` | numeric(5,2) | Percentual de desconto (1-100) |
| `description` | text | Nome da promoção |
| `is_active` | boolean | Se a promoção está ativa |

**Cálculo do preço final:** `price_brl * (1 - discount_percent / 100)`

---

### `orders`
Pedidos realizados pelos clientes.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `order_id` | integer | PK — Identificador único |
| `customer_id` | integer | FK → `customers` |
| `order_date` | date | Data do pedido |
| `status` | order_status | `pending`, `confirmed`, `shipped`, `delivered`, `cancelled` |
| `total_brl` | numeric(10,2) | Valor total |
| `payment_method` | payment_method | Forma de pagamento |
| `tracking_code` | text | Código de rastreio |
| `estimated_delivery` | date | Previsão de entrega |
| `notes` | text | Observações internas |

**Formas de pagamento:** `pix`, `boleto`, `debit`, `credit_3x`, `credit_6x`, `credit_12x`

---

### `order_items`
Itens individuais de cada pedido.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `order_item_id` | bigint | PK — Auto-incremento |
| `order_id` | integer | FK → `orders` |
| `product_id` | integer | FK → `products` |
| `quantity` | integer | Quantidade comprada |

**Constraint:** Combinação `(order_id, product_id)` é única.

---

## Tipos Enumerados (ENUMs)

Valores controlados que ajudam a IA a entender opções válidas:

```sql
product_status: 'active' | 'discontinued' | 'coming_soon'
order_status:   'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled'
payment_method: 'pix' | 'boleto' | 'debit' | 'credit_3x' | 'credit_6x' | 'credit_12x'
```

---

## Views Pré-definidas

Views otimizadas para consultas frequentes, evitando JOINs manuais:

| View | Descrição | Uso típico |
|------|-----------|------------|
| `v_products_with_category` | Produtos + categoria | Listar produtos com nome da categoria |
| `v_products_with_active_promotion` | Produtos em promoção | Mostrar preço original e com desconto |
| `v_order_details` | Pedidos completos | Detalhes de pedido com cliente e itens |
| `v_sales_summary` | Vendas por produto | Análise de produtos mais vendidos |
| `v_customer_orders_summary` | Resumo por cliente | Histórico e total gasto por cliente |
| `v_inventory_status` | Status do estoque | Alertas de estoque baixo/zerado |

---

## Constraints e Regras de Negócio

| Constraint | Tabela | Regra |
|------------|--------|-------|
| `price_brl > 0` | products | Preço sempre positivo |
| `stock_quantity >= 0` | products | Estoque nunca negativo |
| `discount_percent > 0 AND <= 100` | promotions | Desconto entre 1% e 100% |
| `quantity > 0` | order_items | Quantidade mínima de 1 |
| `estimated_delivery >= order_date` | orders | Entrega não pode ser antes do pedido |

---

## Comportamento de Foreign Keys

| FK | ON UPDATE | ON DELETE | Justificativa |
|----|-----------|-----------|---------------|
| products → categories | CASCADE | RESTRICT | Não permitir excluir categoria com produtos |
| promotions → products | CASCADE | CASCADE | Remover promoções se produto for excluído |
| orders → customers | CASCADE | RESTRICT | Não permitir excluir cliente com pedidos |
| order_items → orders | CASCADE | CASCADE | Remover itens se pedido for excluído |
| order_items → products | CASCADE | RESTRICT | Não permitir excluir produto já vendido |

---

## Integração Supabase + GitHub

1. Conecte o repositório em **Project Settings → Integrations → GitHub**
2. Configure:
   - **Working directory:** `.` (raiz do repositório)
   - **Production branch:** `main`
3. As migrations serão aplicadas automaticamente a cada push na `main`

---

## Exemplos de Consultas SQL

### Produtos mais vendidos
```sql
SELECT * FROM v_sales_summary 
ORDER BY total_units_sold DESC 
LIMIT 10;
```

### Clientes que mais gastaram
```sql
SELECT * FROM v_customer_orders_summary 
ORDER BY total_spent DESC 
LIMIT 10;
```

### Produtos com estoque baixo
```sql
SELECT * FROM v_inventory_status 
WHERE stock_level IN ('out_of_stock', 'low_stock');
```

### Produtos em promoção
```sql
SELECT * FROM v_products_with_active_promotion;
```

### Pedidos de um cliente específico
```sql
SELECT * FROM v_order_details 
WHERE customer_id = 3 
ORDER BY order_date DESC;
```
