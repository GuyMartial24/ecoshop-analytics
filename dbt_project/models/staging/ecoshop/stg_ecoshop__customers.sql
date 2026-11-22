-- Clients du back-office : nettoyage et nommage standardisé (1 ligne = 1 client)

with source as (

    select * from {{ source('ecoshop', 'customers') }}

),

renamed as (

    select
        customer_id,
        trim(first_name)                as first_name,
        trim(last_name)                 as last_name,
        -- Correction des défauts de saisie : espaces parasites et majuscules
        lower(trim(email))              as email,
        segment                         as customer_segment,
        postal_code,
        city,
        created_at,
        updated_at,
        _dlt_load_id                    as dlt_load_id

    from source

)

select * from renamed
