-- Communes candidates pour chaque code postal
--
-- Modèle "ephemeral" : il n'est pas créé dans la base. dbt l'injecte sous forme de CTE
-- dans les modèles qui le référencent. Adapté à une petite logique intermédiaire
-- utilisée à un seul endroit et qu'il n'est pas utile d'interroger directement.

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
