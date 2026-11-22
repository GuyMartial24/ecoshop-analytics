{# Macros de calcul financier #}

{# Montant après remise, arrondi au centime #}
{% macro net_amount(quantity, unit_price, discount_rate) -%}
    round(({{ quantity }}) * ({{ unit_price }}) * (1 - coalesce({{ discount_rate }}, 0)), 2)
{%- endmacro %}


{# Montant TTC -> HT (taux par défaut : var vat_rate) #}
{% macro amount_excl_vat(amount_incl_vat, vat_rate=none) -%}
    {%- set rate = vat_rate if vat_rate is not none else var('vat_rate') -%}
    round(({{ amount_incl_vat }}) / (1 + {{ rate }}), 2)
{%- endmacro %}
