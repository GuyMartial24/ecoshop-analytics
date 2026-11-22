-- Lignes de commande : 1 ligne par article.
-- Le lien dlt (_dlt_parent_id) est remplacé par order_id.

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
