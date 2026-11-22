-- Catalogue produits (1 ligne = 1 produit)

with source as (

    select * from {{ source('ecoshop', 'products') }}

),

renamed as (

    select
        product_id,
        product_name,
        category                        as product_category,
        -- Montants : passage de float à numeric pour des calculs monétaires exacts
        unit_price::numeric(12, 2)      as list_price,
        unit_cost::numeric(12, 2)       as unit_cost

    from source

)

select * from renamed
