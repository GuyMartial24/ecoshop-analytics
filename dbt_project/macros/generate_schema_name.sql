{#
    Surcharge du nommage des schémas.

    Comportement par défaut de dbt : <schéma du target>_<schéma personnalisé>
    (ex. analytics_staging), peu lisible pour une architecture médaillon.

    Ici :
    - en dev et en prod, le schéma personnalisé est utilisé tel quel (staging, marts...) ;
    - dans tout autre target (CI), il est préfixé pour isoler chaque exécution
      (ex. ci_pr_12_staging), afin de ne jamais écraser les schémas de dev ou de prod.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name in ["dev", "prod"] -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
