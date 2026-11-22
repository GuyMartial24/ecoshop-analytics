-- Lignes de commande valorisées (1 ligne = 1 article d'une commande)
--
-- Les prix catalogue sont TTC (vente aux particuliers) ; le coût d'achat est HT.
-- La marge se calcule donc sur le montant HT : marge = CA net HT - coût.

with items as (

    select * from {{ ref('stg_ecoshop__order_items') }}

),

products as (

    select * from {{ ref('stg_ecoshop__products') }}

),

amounts as (

    select
        items.order_item_id,
        items.order_id,
        items.line_number,
        items.product_id,
        products.product_category,
        items.quantity,
        items.unit_price,
        items.discount_rate,
        products.unit_cost,

        round(items.quantity * items.unit_price, 2)                                 as gross_amount_incl_vat,
        {{ net_amount('items.quantity', 'items.unit_price', 'items.discount_rate') }} as net_amount_incl_vat,
        round(items.quantity * products.unit_cost, 2)                               as cost_amount

    from items
    inner join products
        on items.product_id = products.product_id

),

final as (

    select
        *,
        gross_amount_incl_vat - net_amount_incl_vat                  as discount_amount,
        {{ amount_excl_vat('net_amount_incl_vat') }}                   as net_amount_excl_vat,
        {{ amount_excl_vat('net_amount_incl_vat') }} - cost_amount     as margin_amount

    from amounts

)

select * from final
