-- Résultats des tests dbt enregistrés par Elementary : 1 ligne par
-- exécution de test.

select
    id                              as test_result_id,
    detected_at,
    detected_at::date               as test_date,
    test_short_name                 as test_name,
    test_type,
    schema_name,
    table_name,
    column_name,
    status,
    failures

from {{ ref('elementary', 'elementary_test_results') }}
