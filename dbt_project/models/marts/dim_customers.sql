-- Dimension client (1 ligne = 1 client, état courant)
--
-- Minimisation des données (RGPD) : l'email et le nom de famille ne sont pas exposés
-- dans la couche BI ; seuls le prénom et l'initiale du nom sont conservés.
-- Les indicateurs de cycle de vie ne portent que sur les commandes comptées dans le CA.

with customers as (

    select * from {{ ref('int_customers_geolocated') }}

),

orders as (

    select * from {{ ref('int_orders_enriched') }}
    where is_revenue

),

order_history as (

    select
        customer_id,
        min(order_date)                 as first_order_date,
        max(order_date)                 as last_order_date,
        count(*)                        as order_count,
        sum(net_amount_incl_vat)        as lifetime_revenue_incl_vat,
        sum(margin_amount)              as lifetime_margin

    from orders
    group by customer_id

)

select
    customers.customer_id,
    customers.first_name || ' ' || left(customers.last_name, 1) || '.'  as customer_display_name,
    customers.customer_segment,
    customers.commune_code,
    customers.postal_code,
    customers.created_at                                                as customer_created_at,
    order_history.first_order_date,
    order_history.last_order_date,
    coalesce(order_history.order_count, 0)                              as order_count,
    coalesce(order_history.lifetime_revenue_incl_vat, 0)                as lifetime_revenue_incl_vat,
    coalesce(order_history.lifetime_margin, 0)                          as lifetime_margin

from customers
left join order_history
    on customers.customer_id = order_history.customer_id
