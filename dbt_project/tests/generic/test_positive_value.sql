{# Valeurs strictement positives (ou >= 0 avec allow_zero).
   Les valeurs nulles sont ignorées. #}

{% test positive_value(model, column_name, allow_zero=false) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} {{ '<' if allow_zero else '<=' }} 0

{% endtest %}
