{%- extends "html.tpl" -%}
{%- block head %}
        {{ super() }}

		<link rel="stylesheet" href="css/marked_custom.css" />

        <script src="{{cdn}}/highlight.min.js"></script>
        {%- for lang in hljlang %}
        <script src="{{cdn}}/languages/{{ lang }}.min.js"></script>
        {%- endfor %}
        
		<!-- Theme used for syntax highlighting of code -->
		<link rel="stylesheet" href="{{cdn}}/highlight-{{hljstyle}}.min.css" />

{%- endblock head %}

{%- block body %}
        {%- block slides %}
        {%- endblock slides %}

        <!-- Javascript libraries configuration and initialisation -->

        <script>
            // Highlighting of every raw code blocks
            hljs.initHighlightingOnLoad();
        </script>

        <script src="{{cdn}}/marked.min.js"></script>
		<script>
            // Set options
            // `highlight` example uses `highlight.js`
            marked.setOptions({
                renderer: new marked.Renderer(),
                highlight: function(code) {
                    return '<div class="hljs">' + hljs.highlightAuto(code).value + '</div>';
                },
                gfm: true,  // GitHub Flavored Markdown (GFM) 
                smartLists: true,
                smartypants: false,
                xhtml: true,
            });
            {%- block markedinit-%}
            {%- endblock markedinit %}
		</script>
{%- endblock body %}
