-- Faits commandes : 1 ligne par commande.
-- Incrémental (merge sur order_id), avec une fenêtre de rattrapage
-- de orders_lookback_days jours. Contrat défini dans _marts.yml.

{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        on_schema_change='fail'
    )
}}

with orders as (

    select * from {{ ref('int_orders_enriched') }}

    {% if is_incremental() %}
    where updated_at > (
        select max(updated_at) - interval '{{ var("orders_lookback_days") }} days'
        from {{ this }}
    )
    {% endif %}

),

customer_versions as (

    select * from {{ ref('dim_customers_history') }}

)

select
    orders.order_id,
    orders.customer_id,
    -- Version du client à la date de la commande
    customer_versions.customer_version_id,
    customer_versions.customer_segment              as customer_segment_at_order,
    customer_versions.commune_code,
    orders.order_date,
    orders.ordered_at,
    orders.updated_at,
    orders.order_status,
    orders.order_status_label,
    orders.is_revenue,
    orders.is_final,
    orders.item_count,
    orders.total_quantity,
    -- Mêmes types que le contrat (sinon on_schema_change échoue)
    orders.gross_amount_incl_vat::numeric(14, 2)    as gross_amount_incl_vat,
    orders.discount_amount::numeric(14, 2)          as discount_amount,
    orders.net_amount_incl_vat::numeric(14, 2)      as net_amount_incl_vat,
    orders.net_amount_excl_vat::numeric(14, 2)      as net_amount_excl_vat,
    orders.cost_amount::numeric(14, 2)              as cost_amount,
    orders.margin_amount::numeric(14, 2)            as margin_amount

from orders
left join customer_versions
    on orders.customer_id = customer_versions.customer_id
    and orders.ordered_at < customer_versions.valid_to
    -- Avant la première version connue : on prend la première version
    and (
        orders.ordered_at >= customer_versions.valid_from
        or customer_versions.is_first_version
    )
