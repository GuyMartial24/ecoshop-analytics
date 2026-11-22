{# Horodatage des snapshots en timestamptz, comme updated_at. #}

{% macro postgres__snapshot_get_time() -%}
    now()::timestamptz
{%- endmacro %}
