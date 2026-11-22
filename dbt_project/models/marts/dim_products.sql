-- Dimension produit (1 ligne = 1 produit)

with products as (

    select * from {{ ref('stg_ecoshop__products') }}

)

select
    product_id,
    product_name,
    product_category,
    list_price                                              as list_price_incl_vat,
    {{ amount_excl_vat('list_price') }}                     as list_price_excl_vat,
    unit_cost,
    {{ amount_excl_vat('list_price') }} - unit_cost         as unit_margin

from products
