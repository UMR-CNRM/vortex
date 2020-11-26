{%- extends 'rst.tpl' -%}

{% block input %}
{%- if cell.input.strip() -%}
.. code:: python

{{ cell.input | indent }}
{%- endif %}
{% endblock input %}

{% block pyerr %}
.. raw:: html

    <div class="nb2sphinx-tb">
{%- for line in output.traceback -%}
{{ line | strip_ansi | indent(4) }}
{%- endfor %}
    </div>

{% endblock pyerr %}

{% block stream %}
.. raw:: html

    <div class="nb2sphinx-stdout">{{ output.text | escape | indent(4) | trim }}</div>

{% endblock stream %}

{% block data_text scoped %}
.. raw:: html

    <div class="nb2sphinx-output">
{%- for line in output.data['text/plain'].split('\n') -%}
    {%- if loop.first -%}
        {%- set outheader = '<span class="output_indicator">Out: </span>' -%}
    {%- else -%}
        {%- set outheader = '         ' -%}
    {%- endif -%}
    {{ outheader }}{{ line | escape }}
{%- endfor -%}
    </div>

{% endblock data_text %}