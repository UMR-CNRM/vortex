{%- extends "html.tpl" -%}
{%- block head %}
        {{ super() }}

		<meta name="viewport" content="width=device-width, initial-scale=1.0" />

		<link rel="stylesheet" href="{{revealjs}}/css/reset.css" />
		<link rel="stylesheet" href="{{revealjs}}/css/reveal.css" />
		<link rel="stylesheet" href="{{revealjs}}/css/theme/white.css" id="theme" />
		<link rel="stylesheet" href="css/reveal_custom.css" />

        
		<!-- Theme used for syntax highlighting of code -->
		<link rel="stylesheet" href="{{cdn}}/highlight-{{hljstyle}}.min.css" />

		<!-- Printing and PDF exports -->
		<script>
			var link = document.createElement( 'link' );
			link.rel = 'stylesheet';
			link.type = 'text/css';
			link.href = window.location.search.match( /print-pdf/gi ) ? '{{revealjs}}/css/print/pdf.css' : '{{revealjs}}/css/print/paper.css';
			document.getElementsByTagName( 'head' )[0].appendChild( link );
		</script>
{%- endblock head %}

{%- block body %}
		<div class="reveal">
			<div class="slides">
            {%- block slides %}
            {%- endblock slides %}
			</div>
		</div>

        <!-- Javascript libraries configuration and initialisation -->

		<script src="{{revealjs}}/js/reveal.js"></script>
		<script>
			Reveal.initialize({

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

				// Add the current slide number to the URL hash so that reloading the
				// page/copying the URL will return you to the same slide
				hash: true,

				// Push each slide change to the browser history. Implies `hash: true`
				history: false,

				// Enable keyboard shortcuts for navigation
				keyboard: true,

				// Enable the slide overview mode
				overview: true,

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

				// Parallax background image
				parallaxBackgroundImage: '', // e.g. "'https://s3.amazonaws.com/hakim-static/reveal-js/reveal-parallax-1.jpg'"

				// Parallax background size
				parallaxBackgroundSize: '', // CSS syntax, e.g. "2100px 900px"

				// Number of pixels to move the parallax background per slide
				// - Calculated automatically unless specified
				// - Set to 0 to disable movement along an axis
				parallaxBackgroundHorizontal: null,
				parallaxBackgroundVertical: null,

				// The display mode that will be used to show slides
				display: 'block',

				// Dependencies to external libs
				dependencies: [
					// Interpret Markdown in <section> elements
					{ src: '{{revealjs}}/plugin/markdown/marked.js', condition: function() { return !!document.querySelector( '[data-markdown]' ); } },
					{ src: '{{revealjs}}/plugin/markdown/markdown.js', condition: function() { return !!document.querySelector( '[data-markdown]' ); } },

					// Syntax highlight for <code> elements
					{ src: '{{revealjs}}/plugin/highlight/highlight.js', async: true },

					// Zoom in and out with Alt+click
					{ src: '{{revealjs}}/plugin/zoom-js/zoom.js', async: true },

					// Speaker notes
					{ src: '{{revealjs}}/plugin/notes/notes.js', async: true },

					// MathJax
					{ src: '{{revealjs}}/plugin/math/math.js', async: true },
				],
			});
		</script>
{%- endblock body %}
