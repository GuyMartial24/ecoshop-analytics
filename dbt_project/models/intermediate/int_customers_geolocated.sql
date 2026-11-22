-- Clients rattachés à leur commune officielle (1 ligne = 1 client)
--
-- Le back-office ne connaît que le code postal et la ville. Un code postal pouvant
-- correspondre à plusieurs communes (ex. 75011 = Paris et Paris 11e Arrondissement),
-- on retient la meilleure candidate, dans cet ordre de priorité :
--   1. le nom de la commune commence par la ville saisie ;
--   2. l'arrondissement plutôt que la commune entière (plus précis, cohérent avec DVF) ;
--   3. la commune la plus peuplée.

with customers as (

    select * from {{ ref('stg_ecoshop__customers') }}

),

candidates as (

    select * from {{ ref('int_postal_code_communes') }}

),

ranked as (

    select
        customers.customer_id,
        candidates.commune_code,
        row_number() over (
            partition by customers.customer_id
            order by
                (candidates.commune_name ilike customers.city || '%') desc,
                candidates.is_municipal_district desc,
                candidates.population desc nulls last
        ) as match_rank

    from customers
    left join candidates
        on customers.postal_code = candidates.postal_code

),

final as (

    select
        customers.*,
        ranked.commune_code

    from customers
    inner join ranked
        on customers.customer_id = ranked.customer_id
        and ranked.match_rank = 1

)

select * from final
