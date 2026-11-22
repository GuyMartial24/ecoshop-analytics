-- Table de faits des lignes de commande (1 ligne = 1 article d'une commande)
-- Grain le plus fin, pour les analyses par produit et par catégorie.

with items as (

    select * from {{ ref('int_order_items_enriched') }}

),

orders as (

    select order_id, customer_id, order_date, order_status, is_revenue
    from {{ ref('int_orders_enriched') }}

)

select
    items.order_item_id,
    items.order_id,
    orders.customer_id,
    items.product_id,
    orders.order_date,
    orders.order_status,
    orders.is_revenue,
    items.quantity,
    items.unit_price,
    items.discount_rate,
    items.gross_amount_incl_vat,
    items.discount_amount,
    items.net_amount_incl_vat,
    items.net_amount_excl_vat,
    items.cost_amount,
    items.margin_amount

from items
inner join orders
    on items.order_id = orders.order_id
