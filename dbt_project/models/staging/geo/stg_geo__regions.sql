-- Régions (1 ligne = 1 région)

with source as (

    select * from {{ source('geo', 'regions') }}

),

renamed as (

    select
        code                            as region_code,
        nom                             as region_name

    from source

)

select * from renamed
