# vortex-templating:jinja2
Header line.
{% for var in listvar  -%}
This is jinja2 tpl. Line {{ "%02d" | format(loop.index)  }}. Input {{ var }}.
{% endfor -%}
Footer line.