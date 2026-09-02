-- =============================================================================
-- SCHEMA: Loja de Instrumentos Musicais
-- Domínio: E-commerce de instrumentos musicais em Mato Grosso do Sul
-- Objetivo: Estrutura otimizada para consultas SQL por IA
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TIPOS ENUMERADOS (ajudam a IA a entender valores válidos)
-- -----------------------------------------------------------------------------

create type public.product_status as enum ('active', 'discontinued', 'coming_soon');
create type public.order_status as enum ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled');
create type public.payment_method as enum ('pix', 'boleto', 'debit', 'credit_3x', 'credit_6x', 'credit_12x');

-- -----------------------------------------------------------------------------
-- TABELA: categories
-- Categorias de instrumentos musicais vendidos na loja
-- Relacionamento: Uma categoria possui muitos produtos (1:N com products)
-- -----------------------------------------------------------------------------

create table public.categories (
  category_id integer primary key,
  name text not null unique,
  description text
);

comment on table public.categories is 'Categorias de instrumentos musicais (ex: Guitarras, Baixos, Violões, Ukuleles, Teclados, Baterias, Sopros)';
comment on column public.categories.category_id is 'Identificador único da categoria';
comment on column public.categories.name is 'Nome da categoria (único)';
comment on column public.categories.description is 'Descrição detalhada da categoria';

-- -----------------------------------------------------------------------------
-- TABELA: customers
-- Clientes da loja, localizados em cidades do Mato Grosso do Sul
-- Relacionamento: Um cliente pode fazer muitos pedidos (1:N com orders)
-- -----------------------------------------------------------------------------

create table public.customers (
  customer_id integer primary key,
  name text not null,
  phone text,
  email text unique,
  city text not null
);

comment on table public.customers is 'Clientes da loja. Todos localizados no Mato Grosso do Sul (Campo Grande, Dourados, Três Lagoas, Corumbá, Ponta Porã)';
comment on column public.customers.customer_id is 'Identificador único do cliente';
comment on column public.customers.name is 'Nome completo do cliente';
comment on column public.customers.phone is 'Telefone no formato (67) XXXXX-XXXX';
comment on column public.customers.email is 'E-mail único do cliente';
comment on column public.customers.city is 'Cidade do cliente no MS';

create index idx_customers_city on public.customers (city);
create index idx_customers_email on public.customers (email);

-- -----------------------------------------------------------------------------
-- TABELA: products
-- Produtos (instrumentos musicais) vendidos na loja
-- Relacionamento: Pertence a uma categoria (N:1 com categories)
-- Relacionamento: Pode ter promoções (1:N com promotions)
-- Relacionamento: Pode aparecer em itens de pedido (1:N com order_items)
-- -----------------------------------------------------------------------------

create table public.products (
  product_id integer primary key,
  name text not null,
  price_brl numeric(10, 2) not null check (price_brl > 0),
  category_id integer not null,
  description text,
  stock_quantity integer not null default 0 check (stock_quantity >= 0),
  status public.product_status not null default 'active',
  specs jsonb,
  created_at date not null default current_date,
  
  constraint fk_products_category 
    foreign key (category_id) 
    references public.categories (category_id) 
    on update cascade 
    on delete restrict
);

comment on table public.products is 'Instrumentos musicais à venda. Inclui violões, guitarras, baixos, ukuleles, teclados, baterias e instrumentos de sopro';
comment on column public.products.product_id is 'Identificador único do produto';
comment on column public.products.name is 'Nome comercial do produto (marca + modelo)';
comment on column public.products.price_brl is 'Preço em Reais (BRL). Para preço com desconto, consultar tabela promotions';
comment on column public.products.category_id is 'FK para categories. Define o tipo de instrumento';
comment on column public.products.description is 'Descrição detalhada do produto';
comment on column public.products.stock_quantity is 'Quantidade disponível em estoque. Zero = indisponível';
comment on column public.products.status is 'Status do produto: active (à venda), discontinued (descontinuado), coming_soon (em breve)';
comment on column public.products.specs is 'Especificações técnicas em JSON (top, back_sides, neck, strings, scale, electronics, color, body, keys, shells, etc.)';
comment on column public.products.created_at is 'Data de cadastro do produto no sistema';

create index idx_products_category_id on public.products (category_id);
create index idx_products_status on public.products (status);
create index idx_products_price on public.products (price_brl);
create index idx_products_stock on public.products (stock_quantity);
create index idx_products_specs on public.products using gin (specs);

-- -----------------------------------------------------------------------------
-- TABELA: promotions
-- Promoções/descontos aplicáveis a produtos específicos
-- Relacionamento: Pertence a um produto (N:1 com products)
-- -----------------------------------------------------------------------------

create table public.promotions (
  promotion_id integer primary key,
  product_id integer not null,
  discount_percent numeric(5, 2) not null check (discount_percent > 0 and discount_percent <= 100),
  description text not null,
  is_active boolean not null default false,
  
  constraint fk_promotions_product 
    foreign key (product_id) 
    references public.products (product_id) 
    on update cascade 
    on delete cascade
);

comment on table public.promotions is 'Promoções e descontos por produto. Use is_active=true para filtrar promoções vigentes';
comment on column public.promotions.promotion_id is 'Identificador único da promoção';
comment on column public.promotions.product_id is 'FK para products. Produto que recebe o desconto';
comment on column public.promotions.discount_percent is 'Percentual de desconto (1-100). Preço final = price_brl * (1 - discount_percent/100)';
comment on column public.promotions.description is 'Nome/motivo da promoção (ex: Black Friday, Liquidação de Inverno)';
comment on column public.promotions.is_active is 'Se true, promoção está ativa e o desconto deve ser aplicado';

create index idx_promotions_product_id on public.promotions (product_id);
create index idx_promotions_active on public.promotions (is_active) where is_active = true;

-- -----------------------------------------------------------------------------
-- TABELA: orders
-- Pedidos realizados pelos clientes
-- Relacionamento: Pertence a um cliente (N:1 com customers)
-- Relacionamento: Possui muitos itens (1:N com order_items)
-- -----------------------------------------------------------------------------

create table public.orders (
  order_id integer primary key,
  customer_id integer not null,
  order_date date not null,
  status public.order_status not null default 'pending',
  total_brl numeric(10, 2) not null check (total_brl >= 0),
  payment_method public.payment_method not null,
  tracking_code text,
  estimated_delivery date,
  notes text,
  
  constraint fk_orders_customer 
    foreign key (customer_id) 
    references public.customers (customer_id) 
    on update cascade 
    on delete restrict,
    
  constraint chk_delivery_after_order 
    check (estimated_delivery is null or estimated_delivery >= order_date)
);

comment on table public.orders is 'Pedidos de compra. Um pedido contém um ou mais itens (order_items)';
comment on column public.orders.order_id is 'Identificador único do pedido';
comment on column public.orders.customer_id is 'FK para customers. Cliente que realizou o pedido';
comment on column public.orders.order_date is 'Data em que o pedido foi realizado';
comment on column public.orders.status is 'Status: pending (aguardando), confirmed (confirmado), shipped (enviado), delivered (entregue), cancelled (cancelado)';
comment on column public.orders.total_brl is 'Valor total do pedido em Reais (soma dos itens)';
comment on column public.orders.payment_method is 'Forma de pagamento: pix, boleto, debit, credit_3x/6x/12x (cartão parcelado)';
comment on column public.orders.tracking_code is 'Código de rastreio dos Correios (formato BRXXXXXXXXBR). Preenchido após envio';
comment on column public.orders.estimated_delivery is 'Data prevista de entrega. Preenchido após envio';
comment on column public.orders.notes is 'Observações internas (motivo de cancelamento, etc.)';

create index idx_orders_customer_id on public.orders (customer_id);
create index idx_orders_status on public.orders (status);
create index idx_orders_date on public.orders (order_date desc);
create index idx_orders_payment on public.orders (payment_method);

-- -----------------------------------------------------------------------------
-- TABELA: order_items
-- Itens individuais de cada pedido (relacionamento N:N entre orders e products)
-- Relacionamento: Pertence a um pedido (N:1 com orders)
-- Relacionamento: Referencia um produto (N:1 com products)
-- -----------------------------------------------------------------------------

create table public.order_items (
  order_item_id bigint generated always as identity primary key,
  order_id integer not null,
  product_id integer not null,
  quantity integer not null check (quantity > 0),
  
  constraint fk_order_items_order 
    foreign key (order_id) 
    references public.orders (order_id) 
    on update cascade 
    on delete cascade,
    
  constraint fk_order_items_product 
    foreign key (product_id) 
    references public.products (product_id) 
    on update cascade 
    on delete restrict,
    
  constraint uq_order_product unique (order_id, product_id)
);

comment on table public.order_items is 'Itens de pedido. Conecta pedidos a produtos com quantidade. Um pedido pode ter múltiplos itens';
comment on column public.order_items.order_item_id is 'Identificador único do item (auto-incremento)';
comment on column public.order_items.order_id is 'FK para orders. Pedido ao qual este item pertence';
comment on column public.order_items.product_id is 'FK para products. Produto comprado';
comment on column public.order_items.quantity is 'Quantidade comprada deste produto no pedido';

create index idx_order_items_order_id on public.order_items (order_id);
create index idx_order_items_product_id on public.order_items (product_id);

-- =============================================================================
-- VIEWS: Consultas pré-definidas para facilitar análises por IA
-- =============================================================================

-- -----------------------------------------------------------------------------
-- VIEW: v_products_with_category
-- Produtos com nome da categoria (evita join manual)
-- -----------------------------------------------------------------------------

create view public.v_products_with_category as
select 
  p.product_id,
  p.name as product_name,
  p.price_brl,
  p.stock_quantity,
  p.status,
  p.description,
  p.specs,
  p.created_at,
  c.category_id,
  c.name as category_name,
  c.description as category_description
from public.products p
join public.categories c on p.category_id = c.category_id;

comment on view public.v_products_with_category is 'Produtos com informações da categoria. Use para listar produtos sem precisar de JOIN';

-- -----------------------------------------------------------------------------
-- VIEW: v_products_with_active_promotion
-- Produtos que têm promoção ativa, com preço final calculado
-- -----------------------------------------------------------------------------

create view public.v_products_with_active_promotion as
select 
  p.product_id,
  p.name as product_name,
  p.price_brl as original_price,
  pr.discount_percent,
  round(p.price_brl * (1 - pr.discount_percent / 100), 2) as discounted_price,
  round(p.price_brl * pr.discount_percent / 100, 2) as savings,
  pr.description as promotion_name,
  c.name as category_name
from public.products p
join public.promotions pr on p.product_id = pr.product_id and pr.is_active = true
join public.categories c on p.category_id = c.category_id
where p.status = 'active';

comment on view public.v_products_with_active_promotion is 'Produtos com promoção ativa. Inclui preço original, desconto e preço final';

-- -----------------------------------------------------------------------------
-- VIEW: v_order_details
-- Detalhes completos de pedidos com cliente e itens
-- -----------------------------------------------------------------------------

create view public.v_order_details as
select 
  o.order_id,
  o.order_date,
  o.status as order_status,
  o.total_brl,
  o.payment_method,
  o.tracking_code,
  o.estimated_delivery,
  o.notes,
  c.customer_id,
  c.name as customer_name,
  c.email as customer_email,
  c.city as customer_city,
  oi.product_id,
  p.name as product_name,
  oi.quantity,
  p.price_brl as unit_price,
  (oi.quantity * p.price_brl) as line_total,
  cat.name as category_name
from public.orders o
join public.customers c on o.customer_id = c.customer_id
join public.order_items oi on o.order_id = oi.order_id
join public.products p on oi.product_id = p.product_id
join public.categories cat on p.category_id = cat.category_id;

comment on view public.v_order_details is 'Detalhes completos de pedidos. Inclui cliente, itens, produtos e categorias. Uma linha por item';

-- -----------------------------------------------------------------------------
-- VIEW: v_sales_summary
-- Resumo de vendas por produto (para análises de desempenho)
-- -----------------------------------------------------------------------------

create view public.v_sales_summary as
select 
  p.product_id,
  p.name as product_name,
  c.name as category_name,
  p.price_brl,
  p.stock_quantity,
  count(distinct o.order_id) as total_orders,
  coalesce(sum(oi.quantity), 0) as total_units_sold,
  coalesce(sum(oi.quantity * p.price_brl), 0) as total_revenue
from public.products p
join public.categories c on p.category_id = c.category_id
left join public.order_items oi on p.product_id = oi.product_id
left join public.orders o on oi.order_id = o.order_id and o.status not in ('cancelled')
group by p.product_id, p.name, c.name, p.price_brl, p.stock_quantity;

comment on view public.v_sales_summary is 'Resumo de vendas por produto. Exclui pedidos cancelados. Use para análise de produtos mais vendidos';

-- -----------------------------------------------------------------------------
-- VIEW: v_customer_orders_summary
-- Resumo de pedidos por cliente
-- -----------------------------------------------------------------------------

create view public.v_customer_orders_summary as
select 
  c.customer_id,
  c.name as customer_name,
  c.email,
  c.city,
  count(distinct o.order_id) as total_orders,
  count(distinct case when o.status = 'delivered' then o.order_id end) as delivered_orders,
  count(distinct case when o.status = 'cancelled' then o.order_id end) as cancelled_orders,
  coalesce(sum(case when o.status != 'cancelled' then o.total_brl end), 0) as total_spent,
  min(o.order_date) as first_order_date,
  max(o.order_date) as last_order_date
from public.customers c
left join public.orders o on c.customer_id = o.customer_id
group by c.customer_id, c.name, c.email, c.city;

comment on view public.v_customer_orders_summary is 'Resumo de compras por cliente. Inclui total gasto, pedidos entregues/cancelados e datas';

-- -----------------------------------------------------------------------------
-- VIEW: v_inventory_status
-- Status do inventário com alertas de estoque baixo
-- -----------------------------------------------------------------------------

create view public.v_inventory_status as
select 
  p.product_id,
  p.name as product_name,
  c.name as category_name,
  p.price_brl,
  p.stock_quantity,
  p.status,
  case 
    when p.stock_quantity = 0 then 'out_of_stock'
    when p.stock_quantity <= 3 then 'low_stock'
    when p.stock_quantity <= 10 then 'medium_stock'
    else 'in_stock'
  end as stock_level,
  p.stock_quantity * p.price_brl as inventory_value
from public.products p
join public.categories c on p.category_id = c.category_id
where p.status = 'active';

comment on view public.v_inventory_status is 'Status do inventário com nível de estoque (out_of_stock, low_stock, medium_stock, in_stock) e valor em estoque';
