-- Table de faits des commandes (1 ligne = 1 commande)
--
-- Contrat appliqué (voir _marts.yml) : noms, types et contraintes des colonnes sont
-- garantis aux consommateurs (Lightdash). Une modification qui casserait ce contrat
-- fait échouer le build au lieu de casser silencieusement les dashboards.

with orders as (

    select * from {{ ref('int_orders_enriched') }}

),

customers as (

    select customer_id, commune_code from {{ ref('int_customers_geolocated') }}

)

select
    orders.order_id,
    orders.customer_id,
    -- Commune actuelle du client (l'historique des adresses viendra avec le snapshot SCD2)
    customers.commune_code,
    orders.order_date,
    orders.ordered_at,
    orders.updated_at,
    orders.order_status,
    orders.order_status_label,
    orders.is_revenue,
    orders.is_final,
    orders.item_count,
    orders.total_quantity,
    orders.gross_amount_incl_vat,
    orders.discount_amount,
    orders.net_amount_incl_vat,
    orders.net_amount_excl_vat,
    orders.cost_amount,
    orders.margin_amount

from orders
inner join customers
    on orders.customer_id = customers.customer_id
