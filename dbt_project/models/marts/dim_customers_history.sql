-- Historique des clients (SCD2) : 1 ligne par version,
-- valide sur [valid_from, valid_to[.

with versions as (

    select * from {{ ref('snap_customers') }}

),

communes as (

    select * from {{ ref('int_postal_city_communes') }}

)

select
    {{ dbt_utils.generate_surrogate_key(['versions.customer_id', 'versions.dbt_valid_from']) }}
                                                    as customer_version_id,
    versions.customer_id,
    versions.customer_segment,
    versions.postal_code,
    versions.city,
    communes.commune_code,
    versions.dbt_valid_from                         as valid_from,
    versions.dbt_valid_to                           as valid_to,
    versions.dbt_valid_to = '9999-12-31 00:00:00+00'::timestamptz
                                                    as is_current,
    row_number() over (
        partition by versions.customer_id
        order by versions.dbt_valid_from
    ) = 1                                           as is_first_version

from versions
left join communes
    on versions.postal_code = communes.postal_code
    and versions.city = communes.city
