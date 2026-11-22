-- Codes postaux des communes (1 ligne = 1 couple commune / code postal)
--
-- Une commune peut avoir plusieurs codes postaux (Paris en a 20) et un code postal
-- peut couvrir plusieurs communes : la relation est de type plusieurs-à-plusieurs.

with postal_codes as (

    select * from {{ source('geo', 'communes__codes_postaux') }}

),

communes as (

    select code, _dlt_id from {{ source('geo', 'communes') }}

),

renamed as (

    select
        communes.code                   as commune_code,
        postal_codes.value              as postal_code

    from postal_codes
    inner join communes
        on postal_codes._dlt_parent_id = communes._dlt_id

)

select * from renamed
