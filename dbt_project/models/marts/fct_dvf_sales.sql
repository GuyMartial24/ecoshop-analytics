-- Table de faits des ventes immobilières (1 ligne = 1 vente DVF)

with sales as (

    select * from {{ ref('int_dvf_sales') }}

)

select
    mutation_id,
    mutation_date,
    mutation_type,
    sale_category,
    commune_code,
    department_code,
    property_value,
    dwelling_count,
    dwelling_area_m2,
    room_count,
    price_per_m2,
    is_reference_sale,
    is_price_outlier,
    latitude,
    longitude,
    source_file

from sales
