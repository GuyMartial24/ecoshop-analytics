-- Part des commandes du CA vendues à perte : alerte au-delà de 10 %.

{{ config(severity='warn') }}

{% set max_share = 0.10 %}

with orders as (

    select margin_amount
    from {{ ref('fct_orders') }}
    where is_revenue

),

share as (

    select
        count(*) filter (where margin_amount < 0)::numeric / nullif(count(*), 0)
            as negative_margin_share
    from orders

)

select negative_margin_share
from share
where negative_margin_share > {{ max_share }}
