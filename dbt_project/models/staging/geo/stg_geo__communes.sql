-- Communes et arrondissements municipaux officiels (1 ligne = 1 code INSEE)

with source as (

    select * from {{ source('geo', 'communes') }}

),

renamed as (

    select
        code                            as commune_code,
        nom                             as commune_name,
        type                            as commune_type,
        code_departement                as department_code,
        code_region                     as region_code,
        population,
        surface                         as area_hectares,
        latitude,
        longitude,
        type = 'arrondissement-municipal' as is_municipal_district

    from source

)

select * from renamed
