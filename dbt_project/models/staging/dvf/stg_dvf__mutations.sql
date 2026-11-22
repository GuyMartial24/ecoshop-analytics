-- Lignes DVF : 1 ligne par lot ou local d'une mutation.
-- property_value = prix de la mutation entière, répété sur chaque ligne.

with source as (

    select * from {{ source('dvf', 'mutations') }}

),

renamed as (

    select
        -- Mutation
        id_mutation                                     as mutation_id,
        date_mutation                                   as mutation_date,
        nature_mutation                                 as mutation_type,
        valeur_fonciere::numeric(14, 2)                 as property_value,

        -- Localisation
        nullif(concat_ws(' ', adresse_numero, adresse_suffixe, adresse_nom_voie), '')
                                                        as street_address,
        code_postal                                     as postal_code,
        code_commune                                    as commune_code,
        nom_commune                                     as commune_name,
        code_departement                                as department_code,
        id_parcelle                                     as parcel_id,
        latitude,
        longitude,

        -- Bien
        code_type_local                                 as property_type_code,
        type_local                                      as property_type,
        type_local in ('Appartement', 'Maison')         as is_dwelling,
        surface_reelle_bati                             as built_area_m2,
        nombre_pieces_principales                       as room_count,
        surface_terrain                                 as land_area_m2,
        nombre_lots                                     as lot_count,

        -- Traçabilité du chargement dlt
        annee                                           as source_year,
        fichier                                         as source_file,
        version_fichier                                 as source_file_version

    from source

)

select * from renamed
