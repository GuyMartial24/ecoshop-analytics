-- En-têtes de commande dans leur dernier statut connu (1 ligne = 1 commande)

with source as (

    select * from {{ source('ecoshop', 'orders') }}

),

renamed as (

    select
        order_id,
        customer_id,
        status                          as order_status,
        currency,
        created_at                      as ordered_at,
        created_at::date                as order_date,
        updated_at,
        _dlt_load_id                    as dlt_load_id

    from source

)

select * from renamed
