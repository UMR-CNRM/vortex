{%- extends 'rst.tpl' -%}

{% block error %}
.. raw:: html

    <div class="nb2sphinx-tb">
{%- for line in output.traceback %}
{{ line | ansi2html | indent(4) }}
{%- endfor %}
    </div>

{% endblock error %}

{% block stream %}
.. raw:: html

    <div class="nb2sphinx-stdout">
{{ output.text | escape | trim | indent(4) }}
    </div>

{% endblock stream %}

{% block data_text scoped %}
.. raw:: html

    <div class="nb2sphinx-output">
{%- for line in output.data['text/plain'].split('\n') -%}
    {%- if loop.first -%}
        {%- set outheader = '<span class="output_indicator">Out: </span>' -%}
    {%- else -%}
        {%- set outheader = '     ' -%}
    {%- endif %}
{{ outheader | indent }}{{ line | escape }}
{%- endfor %}
    </div>

{% endblock data_text %}
