{#
    Test générique personnalisé : la colonne ne contient que des valeurs positives.

    Utilisable sur n'importe quel modèle depuis un fichier YAML :
        data_tests:
          - positive_value
          - positive_value:
              arguments:
                allow_zero: true

    Comme tout test dbt, il échoue s'il renvoie au moins une ligne.
    Les valeurs nulles sont ignorées (c'est le rôle du test not_null).
#}
{% test positive_value(model, column_name, allow_zero=false) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} {{ '<' if allow_zero else '<=' }} 0

{% endtest %}
