{%- extends "html.tpl" -%}, maximum-scale=1.0, user-scalable=no
{%- block head %}
        {{ super() }}

		<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />

		<link rel="stylesheet" href="{{cdn}}/reveal/reset.min.css" />
		<link rel="stylesheet" href="{{cdn}}/reveal/reveal.min.css" />
		<link rel="stylesheet" href="{{cdn}}/reveal/theme/white.min.css" id="theme" />
		<link rel="stylesheet" href="css/reveal_custom.css" />

        
		<!-- Theme used for syntax highlighting of code -->
		<link rel="stylesheet" href="{{cdn}}/highlight/styles/{{hljstyle}}.min.css" id="highlight-theme" />
        <!-- Extra kanguages for highlight-->
        {%- for lang in hljlang %}
        <script src="{{cdn}}/highlight/languages/{{lang}}.min.js"></script>
        {%- endfor %}
{%- endblock head %}

{%- block body %}
		<div class="reveal">
			<div class="slides">
            {%- block slides %}
            {%- endblock slides %}
			</div>
		</div>

        <!-- Javascript libraries configuration and initialisation -->

		<script src="{{cdn}}/reveal/reveal.min.js"></script>
		<script src="{{cdn}}/reveal/plugin/markdown/markdown.min.js"></script>
		<script src="{{cdn}}/reveal/plugin/highlight/highlight.min.js"></script>
		<script src="{{cdn}}/reveal/plugin/notes/notes.min.js"></script>
		<!-- <script src="{{cdn}}/reveal/plugin/math/math.min.js"></script> -->
		<script>
			Reveal.initialize({

                //math: {
                //    mathjax: '{{cdn}}/mathjax/MathJax.js',
                //},
                // Add this in the list below if  needed: RevealMath,
                plugins: [ RevealMarkdown,
                           RevealHighlight,
                           RevealNotes, ],

				// Display presentation control arrows
				controls: true,

				// Help the user learn the controls by providing hints, for example by
				// bouncing the down arrow when they first encounter a vertical slide
				controlsTutorial: true,

				// Determines where controls appear, "edges" or "bottom-right"
				controlsLayout: 'bottom-right',

				// Visibility rule for backwards navigation arrows; "faded", "hidden"
				// or "visible"
				controlsBackArrows: 'faded',

				// Display a presentation progress bar
				progress: true,

				// Display the page number of the current slide
				slideNumber: true,

                // Can be used to limit the contexts in which the slide number appears
                // - "all":      Always show the slide number
                // - "print":    Only when printing to PDF
                // - "speaker":  Only in the speaker view
                showSlideNumber: 'all',

				// Add the current slide number to the URL hash so that reloading the
				// page/copying the URL will return you to the same slide
				hash: true,

				// Push each slide change to the browser history. Implies `hash: true`
				history: false,

				// Enable keyboard shortcuts for navigation
				keyboard: true,

				// Enable the slide overview mode
				overview: true,

                // Vertical centering of slides
                center: true,

				// See https://github.com/hakimel/reveal.js/#navigation-mode
				navigationMode: 'default',

				// Turns fragments on and off globally
				fragments: true,

				// Flags if we should show a help overlay when the questionmark
				// key is pressed
				help: true,

				// Enable slide navigation via mouse wheel
				mouseWheel: false,

				// Transition style
				transition: 'slide', // none/fade/slide/convex/concave/zoom

				// Transition speed
				transitionSpeed: 'default', // default/fast/slow

				// Transition style for full page slide backgrounds
				backgroundTransition: 'fade', // none/fade/slide/convex/concave/zoom

				// Number of slides away from the current that are visible
				viewDistance: 3,

				// The display mode that will be used to show slides
				display: 'block',
			});
		</script>
{%- endblock body %}
