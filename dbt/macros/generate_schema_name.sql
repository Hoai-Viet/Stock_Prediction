{% macro generate_schema_name(custom_schema_name, node) -%}
    {#-- 
        Override default behavior to use 'dwh' schema directly
        instead of concatenating target_schema + custom_schema (dwh_dwh)
    --#}
    
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
    
{%- endmacro %}
