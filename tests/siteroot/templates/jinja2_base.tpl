{%- block header -%}
Header line.
{% endblock -%}
{%- block content -%}
{%- for var in listvar  -%}
{%- set ivar = loop.index -%}
This is jinja2 tpl. Line {% block linedisp scoped -%} {{ ivar }}{% endblock %}. Input {% block vardisp scoped -%}{{ var }}{% endblock %}.
{% endfor -%}
{%- endblock -%}
{%- block footer -%}
Footer line.
{%- endblock footer -%}