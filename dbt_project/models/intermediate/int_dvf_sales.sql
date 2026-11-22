-- Ventes immobilières DVF au grain de la mutation (1 ligne = 1 vente)
--
-- Dans la source, une vente occupe une ligne par lot ou local, et son prix est répété
-- sur chacune de ces lignes. Sommer ce prix au grain ligne multiplierait les montants :
-- on remonte donc au grain mutation avant tout calcul.
--
-- Prix au m² : calculé uniquement sur les ventes "de référence" (une vente simple
-- portant sur un seul logement), sinon la surface ou le prix seraient ambigus.

with lines as (

    select * from {{ ref('stg_dvf__mutations') }}

),

per_mutation as (

    select
        mutation_id,
        min(mutation_date)                                      as mutation_date,
        min(mutation_type)                                      as mutation_type,
        -- Prix identique sur toutes les lignes d'une mutation (vérifié) : max() le dédoublonne
        max(property_value)                                     as property_value,
        -- Commune majoritaire si la vente porte sur plusieurs communes
        mode() within group (order by commune_code)             as commune_code,
        min(department_code)                                    as department_code,
        count(distinct commune_code)                            as commune_count,
        count(*)                                                as line_count,
        count(*) filter (where is_dwelling)                     as dwelling_count,
        count(*) filter (where property_type = 'Appartement')   as apartment_count,
        count(*) filter (where property_type = 'Maison')        as house_count,
        (sum(built_area_m2) filter (where is_dwelling))::numeric(12, 2)
                                                                as dwelling_area_m2,
        max(room_count) filter (where is_dwelling)              as room_count,
        avg(latitude)                                           as latitude,
        avg(longitude)                                          as longitude,
        min(source_file)                                        as source_file

    from lines
    group by mutation_id

),

classified as (

    select
        *,
        case
            when apartment_count = 1 and house_count = 0 then 'Appartement'
            when house_count = 1 and apartment_count = 0 then 'Maison'
            when dwelling_count > 1                      then 'Plusieurs logements'
            else 'Hors logement'
        end                                                     as sale_category,
        (
            mutation_type = 'Vente'
            and dwelling_count = 1
            and dwelling_area_m2 > 0
            and property_value > 0
        )                                                       as is_reference_sale

    from per_mutation

),

final as (

    select
        *,
        case
            when is_reference_sale then round(property_value / dwelling_area_m2, 2)
        end                                                     as price_per_m2,
        -- Ventes de référence au prix au m² hors bornes : exclues des moyennes
        is_reference_sale and not (
            property_value / dwelling_area_m2
                between {{ var('dvf_min_price_per_m2') }} and {{ var('dvf_max_price_per_m2') }}
        )                                                       as is_price_outlier

    from classified

)

select * from final
