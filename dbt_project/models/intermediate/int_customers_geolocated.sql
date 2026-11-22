-- Clients (état courant) rattachés à leur commune officielle (1 ligne = 1 client)
-- La règle de rattachement est centralisée dans int_postal_city_communes.

with customers as (

    select * from {{ ref('stg_ecoshop__customers') }}

),

communes as (

    select * from {{ ref('int_postal_city_communes') }}

)

select
    customers.*,
    communes.commune_code

from customers
left join communes
    on customers.postal_code = communes.postal_code
    and customers.city = communes.city
