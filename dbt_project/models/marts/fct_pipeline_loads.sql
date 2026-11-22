-- Chargements dlt des trois sources : 1 ligne par chargement.
-- Pour le back-office, nombre de lignes dont c'est le dernier chargement.

with loads as (

    select 'ecoshop' as pipeline, load_id, status, inserted_at
    from {{ source('ecoshop', '_dlt_loads') }}

    union all

    select 'geo' as pipeline, load_id, status, inserted_at
    from {{ source('geo', '_dlt_loads') }}

    union all

    select 'dvf' as pipeline, load_id, status, inserted_at
    from {{ source('dvf', '_dlt_loads') }}

),

orders_per_load as (

    select _dlt_load_id as load_id, count(*) as orders_rows
    from {{ source('ecoshop', 'orders') }}
    group by 1

),

customers_per_load as (

    select _dlt_load_id as load_id, count(*) as customers_rows
    from {{ source('ecoshop', 'customers') }}
    group by 1

)

select
    loads.pipeline || '-' || loads.load_id      as pipeline_load_id,
    loads.pipeline,
    loads.load_id,
    loads.inserted_at,
    loads.inserted_at::date                     as load_date,
    loads.status = 0                            as is_success,
    coalesce(orders_per_load.orders_rows, 0)    as orders_rows,
    coalesce(customers_per_load.customers_rows, 0) as customers_rows

from loads
left join orders_per_load
    on loads.pipeline = 'ecoshop'
    and loads.load_id = orders_per_load.load_id
left join customers_per_load
    on loads.pipeline = 'ecoshop'
    and loads.load_id = customers_per_load.load_id
