-- Commandes avec leurs montants agrégés et les règles de gestion du statut
-- (1 ligne = 1 commande)

with orders as (

    select * from {{ ref('stg_ecoshop__orders') }}

),

statuses as (

    select * from {{ ref('order_status_mapping') }}

),

items as (

    select * from {{ ref('int_order_items_enriched') }}

),

items_per_order as (

    select
        order_id,
        count(*)                        as item_count,
        sum(quantity)::bigint           as total_quantity,
        sum(gross_amount_incl_vat)      as gross_amount_incl_vat,
        sum(discount_amount)            as discount_amount,
        sum(net_amount_incl_vat)        as net_amount_incl_vat,
        sum(net_amount_excl_vat)        as net_amount_excl_vat,
        sum(cost_amount)                as cost_amount,
        sum(margin_amount)              as margin_amount

    from items
    group by order_id

),

final as (

    select
        orders.order_id,
        orders.customer_id,
        orders.order_date,
        orders.ordered_at,
        orders.updated_at,
        orders.order_status,
        statuses.order_status_label,
        statuses.is_revenue,
        statuses.is_final,
        orders.currency,
        items_per_order.item_count,
        items_per_order.total_quantity,
        items_per_order.gross_amount_incl_vat,
        items_per_order.discount_amount,
        items_per_order.net_amount_incl_vat,
        items_per_order.net_amount_excl_vat,
        items_per_order.cost_amount,
        items_per_order.margin_amount

    from orders
    inner join statuses
        on orders.order_status = statuses.order_status
    inner join items_per_order
        on orders.order_id = items_per_order.order_id

)

select * from final
