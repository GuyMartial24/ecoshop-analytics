-- Communes candidates pour chaque code postal (ephemeral).

{{ config(materialized='ephemeral') }}

select
    postal_codes.postal_code,
    communes.commune_code,
    communes.commune_name,
    communes.is_municipal_district,
    communes.population

from {{ ref('stg_geo__commune_postal_codes') }} as postal_codes
inner join {{ ref('stg_geo__communes') }} as communes
    on postal_codes.commune_code = communes.commune_code
