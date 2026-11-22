-- Les versions d'un client se suivent sans trou ni chevauchement,
-- et seule la dernière est la version courante.

with versions as (

    select
        customer_id,
        customer_version_id,
        valid_from,
        valid_to,
        is_current,
        lead(valid_from) over (partition by customer_id order by valid_from) as next_valid_from

    from {{ ref('dim_customers_history') }}

)

select *
from versions
where
    -- trou ou chevauchement
    (next_valid_from is not null and valid_to <> next_valid_from)
    -- version courante qui n'est pas la dernière
    or (next_valid_from is not null and is_current)
    -- dernière version qui n'est pas courante
    or (next_valid_from is null and not is_current)
    -- période vide ou inversée
    or valid_from >= valid_to
