-- Correspondance commune / code postal (plusieurs-à-plusieurs).

with postal_codes as (

    select * from {{ source('geo', 'communes__codes_postaux') }}

),

communes as (

    select code, _dlt_id from {{ source('geo', 'communes') }}

),

renamed as (

    select
        {{ dbt_utils.generate_surrogate_key(['communes.code', 'postal_codes.value']) }}
                                        as commune_postal_code_id,
        communes.code                   as commune_code,
        postal_codes.value              as postal_code

    from postal_codes
    inner join communes
        on postal_codes._dlt_parent_id = communes._dlt_id

)

select * from renamed
