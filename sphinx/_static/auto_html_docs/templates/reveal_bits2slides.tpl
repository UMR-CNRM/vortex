{%- macro addsection(slide) -%}
{%- if slide.type == 'md' -%}
<section data-markdown {{ slide.args }}>
    <script type="text/template">
{{ slide.content }}
    </script>
</section>
{%- endif %}
{%- if slide.type == 'ht' -%}
<section {{ slide.args }}>
{{ slide.content }}
</section>
{%- endif %}
{%- endmacro -%}

{%- extends "reveal_base.tpl" %}
{%- block slides %}
            <!-- Automatic content generation starts here -->
			{%- for slide1 in slides -%}
                {%- if slide1|length > 1 %}

                <!-- Starting Slides Group #{{ loop.index }}  -->
				<section>
				{%- for slide2 in slide1 %}

<!-- New Sub-Slide -->
{{ addsection(slide2) }}
				{%- endfor %}

                <!-- Ending   Slides Group #{{ loop.index }} -->
				</section>
				{%- else %}

<!-- New Slide -->
{{ addsection(slide1[0]) }}
				{%- endif -%}
            {%- endfor %}
            <!-- Automatic content generation ends here -->
{%- endblock slides %}
