-- Dimension géographique (1 ligne = 1 commune ou arrondissement municipal)
-- Sert à la cartographie Lightdash et aux analyses par département ou région.

with communes as (

    select * from {{ ref('stg_geo__communes') }}

),

departments as (

    select * from {{ ref('stg_geo__departments') }}

),

regions as (

    select * from {{ ref('stg_geo__regions') }}

)

select
    communes.commune_code,
    communes.commune_name,
    communes.commune_type,
    communes.is_municipal_district,
    communes.department_code,
    departments.department_name,
    communes.region_code,
    regions.region_name,
    communes.population,
    communes.area_hectares,
    communes.latitude,
    communes.longitude

from communes
left join departments
    on communes.department_code = departments.department_code
left join regions
    on communes.region_code = regions.region_code
