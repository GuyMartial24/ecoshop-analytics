-- Départements (1 ligne = 1 département)

with source as (

    select * from {{ source('geo', 'departements') }}

),

renamed as (

    select
        code                            as department_code,
        nom                             as department_name,
        code_region                     as region_code

    from source

)

select * from renamed
