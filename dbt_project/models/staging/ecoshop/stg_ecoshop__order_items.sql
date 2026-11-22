-- Lignes de commande (1 ligne = 1 article d'une commande)
--
-- dlt a extrait la liste imbriquée `items` dans une table enfant reliée à sa commande
-- par un identifiant technique (_dlt_parent_id -> orders._dlt_id). On remplace ce lien
-- technique par la clé métier order_id, seule exploitable dans les couches suivantes.

with items as (

    select * from {{ source('ecoshop', 'orders__items') }}

),

orders as (

    select order_id, _dlt_id from {{ source('ecoshop', 'orders') }}

),

renamed as (

    select
        orders.order_id || '-' || items.line_number   as order_item_id,
        orders.order_id,
        items.line_number,
        items.product_id,
        items.quantity,
        items.unit_price::numeric(12, 2)              as unit_price,
        items.discount_rate::numeric(5, 4)            as discount_rate

    from items
    inner join orders
        on items._dlt_parent_id = orders._dlt_id

)

select * from renamed
