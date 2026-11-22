-- Commune de chaque adresse client (code postal, ville), actuelle ou passée.
-- Si plusieurs communes partagent le code postal, priorité :
-- nom qui correspond à la ville, puis arrondissement, puis population.

with addresses as (

    select postal_code, city from {{ ref('stg_ecoshop__customers') }}
    union
    select postal_code, city from {{ ref('snap_customers') }}

),

candidates as (

    select * from {{ ref('int_postal_code_communes') }}

),

ranked as (

    select
        addresses.postal_code,
        addresses.city,
        candidates.commune_code,
        row_number() over (
            partition by addresses.postal_code, addresses.city
            order by
                (candidates.commune_name ilike addresses.city || '%') desc,
                candidates.is_municipal_district desc,
                candidates.population desc nulls last
        ) as match_rank

    from addresses
    left join candidates
        on addresses.postal_code = candidates.postal_code

)

select
    postal_code,
    city,
    commune_code

from ranked
where match_rank = 1
