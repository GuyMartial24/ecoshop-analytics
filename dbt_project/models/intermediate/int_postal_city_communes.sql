-- Résolution d'une adresse (code postal, ville) vers sa commune officielle
-- (1 ligne = 1 couple code postal / ville connu)
--
-- Couvre les adresses actuelles (staging) et passées (snapshot), pour géolocaliser
-- aussi bien l'état courant des clients que leur historique.
-- Un code postal pouvant correspondre à plusieurs communes (ex. 75011 = Paris et
-- Paris 11e Arrondissement), on retient la meilleure candidate, dans cet ordre :
--   1. le nom de la commune commence par la ville saisie ;
--   2. l'arrondissement plutôt que la commune entière (plus précis, cohérent avec DVF) ;
--   3. la commune la plus peuplée.

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
