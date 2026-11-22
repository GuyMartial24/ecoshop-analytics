{#
    Surcharge d'une macro interne de dbt pour PostgreSQL.

    dbt appelle snapshot_get_time() via adapter.dispatch : il cherche d'abord une macro
    nommée <adaptateur>__snapshot_get_time dans le projet, puis celle fournie par dbt.
    Celle de dbt renvoie un timestamp SANS fuseau horaire, alors que nos colonnes
    updated_at / dbt_valid_from sont des timestamptz : on aligne le type.
#}
{% macro postgres__snapshot_get_time() -%}
    now()::timestamptz
{%- endmacro %}
