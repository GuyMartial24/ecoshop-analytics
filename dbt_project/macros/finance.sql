{#
    Macros de calcul financier réutilisables.
    Une macro Jinja génère du SQL à la compilation : la règle de calcul est écrite
    une seule fois et appliquée partout de la même manière.
#}

{# Montant d'une ligne après remise, arrondi au centime #}
{% macro net_amount(quantity, unit_price, discount_rate) -%}
    round(({{ quantity }}) * ({{ unit_price }}) * (1 - coalesce({{ discount_rate }}, 0)), 2)
{%- endmacro %}


{# Conversion d'un montant TTC en HT (taux par défaut : variable vat_rate) #}
{% macro amount_excl_vat(amount_incl_vat, vat_rate=none) -%}
    {%- set rate = vat_rate if vat_rate is not none else var('vat_rate') -%}
    round(({{ amount_incl_vat }}) / (1 + {{ rate }}), 2)
{%- endmacro %}
