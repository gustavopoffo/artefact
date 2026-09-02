-- Schema inicial baseado nos CSVs do desafio técnico

create table public.categories (
  category_id integer primary key,
  name text not null,
  description text
);

create table public.customers (
  customer_id integer primary key,
  name text not null,
  phone text,
  email text,
  city text
);

create table public.products (
  product_id integer primary key,
  price_brl numeric(10, 2) not null,
  name text not null,
  category_id integer not null references public.categories (category_id),
  description text,
  stock_quantity integer not null default 0,
  status text not null,
  specs jsonb,
  created_at date
);

create table public.promotions (
  promotion_id integer primary key,
  product_id integer not null references public.products (product_id),
  discount_percent numeric(5, 2) not null,
  description text,
  is_active boolean not null default false
);

create table public.orders (
  order_id integer primary key,
  customer_id integer not null references public.customers (customer_id),
  order_date date not null,
  status text not null,
  total_brl numeric(10, 2) not null,
  payment_method text,
  tracking_code text,
  estimated_delivery date,
  notes text
);

create table public.order_items (
  order_item_id bigint generated always as identity primary key,
  order_id integer not null references public.orders (order_id) on delete cascade,
  product_id integer not null references public.products (product_id),
  quantity integer not null check (quantity > 0),
  unique (order_id, product_id)
);

create index idx_products_category_id on public.products (category_id);
create index idx_promotions_product_id on public.promotions (product_id);
create index idx_orders_customer_id on public.orders (customer_id);
create index idx_order_items_order_id on public.order_items (order_id);
create index idx_order_items_product_id on public.order_items (product_id);
