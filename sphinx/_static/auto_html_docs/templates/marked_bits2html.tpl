{%- macro addcontainer(i, j, slide) -%}
{%- if slide.type == 'md' %}

<div id='automd-container{{ i }}-{{ j }}'>
{{ slide.content }}
</div>
{%- endif %}
{%- if slide.type == 'ht' %}

{{ slide.content }}
{%- endif %}
{%- endmacro -%}

{%- macro processcontainer(i, j, slide) -%}
{%- if slide.type == 'md' %}
md_container = document.getElementById('automd-container{{ i }}-{{ j }}');
md_container.innerHTML = marked(md_container.textContent);
{%- endif %}
{%- endmacro -%}

{%- extends "marked_base.tpl" %}
{%- block slides %}
        <!-- Automatic content generation starts here: indentation resetted --!>
        {%- for slide1 in slides -%}
        {%- set ifirst=loop.index -%}
        {%- for slide2 in slide1 -%}
{{ addcontainer(ifirst, loop.index, slide2) }}
        {%- endfor %}
        {%- endfor %}
        <!-- Automatic content generation ends here --!>
{%- endblock slides %}
{%- block markedinit %}
        {%- for slide1 in slides -%}
        {%- set ifirst=loop.index -%}
        {%- for slide2 in slide1 -%}
        {{ processcontainer(ifirst, loop.index, slide2)|indent(width=12) }}
        {%- endfor %}
        {%- endfor %}
{%- endblock markedinit %}
