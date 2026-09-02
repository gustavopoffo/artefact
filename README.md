# Artefact

Projeto do desafio técnico com dados de e-commerce musical.

## Estrutura

- `data/` — CSVs de origem (categorias, clientes, produtos, pedidos, etc.)
- `supabase/migrations/` — schema do banco para integração Supabase + GitHub

## Supabase

1. Conecte o repositório no [dashboard do Supabase](https://supabase.com/dashboard) (Integrations → GitHub).
2. Selecione a branch `main`.
3. As migrations em `supabase/migrations/` criarão as tabelas automaticamente.

### Tabelas

| Tabela | Descrição |
|--------|-----------|
| `categories` | Categorias de produtos |
| `customers` | Clientes |
| `products` | Produtos (com `specs` em JSONB) |
| `promotions` | Promoções por produto |
| `orders` | Pedidos |
| `order_items` | Itens de cada pedido |
