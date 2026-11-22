-- Intégrité de l'historique SCD2 : les versions d'un client doivent se suivre sans
-- trou ni chevauchement (la fin d'une version = le début de la suivante), et seule
-- la dernière version peut être la version courante.
-- Sans cette garantie, la jointure temporelle de fct_orders pourrait rattacher une
-- commande à zéro ou à plusieurs versions.

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
    -- trou ou chevauchement avec la version suivante
    (next_valid_from is not null and valid_to <> next_valid_from)
    -- une version courante qui n'est pas la dernière
    or (next_valid_from is not null and is_current)
    -- une dernière version qui n'est pas courante (client non supprimé à la source)
    or (next_valid_from is null and not is_current)
    -- période vide ou inversée
    or valid_from >= valid_to
