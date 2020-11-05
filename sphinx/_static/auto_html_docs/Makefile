# The subdirectory that will holds pre-fetech CDN content
CDN.JS=cdn

# Reveal.js download settings
# ---------------------------
REVEAL.VERSION=4.1.0
REVEAL.CDN=https://cdnjs.cloudflare.com/ajax/libs/reveal.js/$(REVEAL.VERSION)

REVEAL.THEMES=white
REVEAL.FONTS1=source-sans-pro/source-sans-pro.css \
	source-sans-pro/source-sans-pro-italic.eot \
	source-sans-pro/source-sans-pro-italic.ttf \
	source-sans-pro/source-sans-pro-italic.woff \
	source-sans-pro/source-sans-pro-regular.eot \
	source-sans-pro/source-sans-pro-regular.ttf \
	source-sans-pro/source-sans-pro-regular.woff \
	source-sans-pro/source-sans-pro-semibold.eot \
	source-sans-pro/source-sans-pro-semibolditalic.eot \
	source-sans-pro/source-sans-pro-semibolditalic.ttf \
	source-sans-pro/source-sans-pro-semibolditalic.woff \
	source-sans-pro/source-sans-pro-semibold.ttf \
	source-sans-pro/source-sans-pro-semibold.woff
REVEAL.FONTS2=league-gothic/league-gothic.css \
	league-gothic/league-gothic.eot \
	league-gothic/league-gothic.ttf \
	league-gothic/league-gothic.woff
REVEAL.FONTS=$(REVEAL.FONTS1)
REVEAL.PLUGINS=markdown/markdown.min.js \
	math/math.min.js \
	notes/notes.min.js \
	highlight/highlight.min.js
REVEAL.CSS=reset reveal
REVEAL.JS=reveal
REVEAL.STUFF.FONTS=$(patsubst %, $(CDN.JS)/reveal/theme/fonts/%, $(REVEAL.FONTS))
REVEAL.STUFF=$(patsubst %, $(CDN.JS)/reveal/theme/%.min.css, $(REVEAL.THEMES)) \
	$(REVEAL.STUFF.FONTS) \
	$(patsubst %, $(CDN.JS)/reveal/plugin/%, $(REVEAL.PLUGINS)) \
	$(patsubst %, $(CDN.JS)/reveal/%.min.css, $(REVEAL.CSS)) \
	$(patsubst %, $(CDN.JS)/reveal/%.min.js, $(REVEAL.JS))

# Highlight download settings
# ---------------------------
HIGHLIGHT.VERSION=10.3.2
HIGHLIGHT.CDN=https://cdnjs.cloudflare.com/ajax/libs/highlight.js/$(HIGHLIGHT.VERSION)

# If you need extra languages (e.g. fortran), this is the place !
# Note: C & Python are included by default
HIGHLIGHT.LANG=
# Code highlighting theme for slides
HIGHLIGHT.STYLE_S=sunburst
# Code highlighting theme for documents
HIGHLIGHT.STYLE_D=github
HIGHLIGHT.STYLES=$(HIGHLIGHT.STYLE_D) $(HIGHLIGHT.STYLE_S)
HIGHLIGHT.JS=highlight
HIGHLIGHT.STUFF=$(patsubst %, $(CDN.JS)/highlight/%.min.js, $(HIGHLIGHT.JS)) \
	$(patsubst %, $(CDN.JS)/highlight/languages/%.min.js, $(HIGHLIGHT.LANG)) \
	$(patsubst %, $(CDN.JS)/highlight/styles/%.min.css, $(HIGHLIGHT.STYLES))

# Marked download settings
# ------------------------
MARKED.VERSION=1.2.2
MARKED.CDN=https://cdnjs.cloudflare.com/ajax/libs/marked/$(MARKED.VERSION)

MARKED.JS=marked
MARKED.STUFF=$(patsubst %, $(CDN.JS)/marked/%.min.js, $(MARKED.JS))

# MathJax download settings
# -------------------------
MATHJAX.VERSION=2.7.9
MATHJAX.CDN=https://cdn.jsdelivr.net/gh/mathjax/mathjax@$(MATHJAX.VERSION)

MATHJAX.JS=MathJax \
	config/TeX-AMS_HTML-full \
	extensions/MathMenu extensions/MathZoom \
	jax/output/HTML-CSS/fonts/TeX/fontdata
MATHJAX.STUFF=$(patsubst %, $(CDN.JS)/mathjax/%.js, $(MATHJAX.JS))

# Document generation settings
# ----------------------------

# All the document ending with .content will be delt with...
MD_BASEEXT=content
MD_BASE=$(wildcard *.$(MD_BASEEXT))
MD_SLIDEEXT=_slides.html
MD_SLIDE=$(patsubst %.$(MD_BASEEXT),%$(MD_SLIDEEXT),$(MD_BASE))
MD_DOCEXT=_doc.html
MD_DOC=$(patsubst %.$(MD_BASEEXT),%$(MD_DOCEXT),$(MD_BASE))

TEMPLATES_DIR=templates
TEMPLATES=$(shell find $(TEMPLATES_DIR) -name '*.tpl')

PYTHON3=python3
PROCESSOR=bin/py_processor.py
PROCESSOR_DEF=$(PYTHON3) $(PROCESSOR) --cdn=$(CDN.JS) --lang='$(HIGHLIGHT.LANG)'

# Automatic image generation
REP_IMAGES_SRC=images_src/
REP_IMAGES_AUTO=images_auto/

IMAGES_SRC_LIST=$(shell find $(REP_IMAGES_SRC) -follow -type f)
# dia -> png
DIASTUFF=$(filter %.dia, $(IMAGES_SRC_LIST))
DIASTUFF_PNG=$(DIASTUFF:$(REP_IMAGES_SRC)%.dia=$(REP_IMAGES_AUTO)%.png)
DIASTUFF_SVG=$(DIASTUFF:$(REP_IMAGES_SRC)%.dia=$(REP_IMAGES_AUTO)%.svg)
# svg -> png
SVGSTUFF=$(filter %.svg, $(IMAGES_SRC_LIST))
SVGSTUFF_PNG=$(SVGSTUFF:$(REP_IMAGES_SRC)%.svg=$(REP_IMAGES_AUTO)%.png)

# Common dependencies (prefer SVG)
COMDEP_IMG_AUTO=$(DIASTUFF_SVG)
# Just in case png is prefered
# COMDEP_IMG_AUTO=$(DIASTUFF_PNG) $(SVGSTUFF_PNG)
COMDEP=$(HIGHLIGHT.STUFF) $(PROCESSOR) $(TEMPLATES) $(COMDEP_IMG_AUTO)

# Because of Meteo-France's we need this proxy :-(
ifdef VORTEX_PROJECT_SSLCERT_OVERRIDE
WGET=wget --ca-certificate=$(VORTEX_PROJECT_SSLCERT_OVERRIDE)
else
WGET=wget
endif

.PHONY: all docs slides clean distclean $(CDN.JS)

.SECONDARY: $(HIGHLIGHT.STUFF) $(MARKED.STUFF) $(REVEAL.STUFF) $(MATHJAX.STUFF) $(COMDEP_IMG_AUTO)

all: $(MD_SLIDE) $(MD_DOC)

docs: $(MD_DOC)

slides: $(MD_SLIDE)

# Fetch various JavaScript libraries

$(MARKED.STUFF):
	@mkdir -p $(dir $@)
	$(WGET) --output-document=$@ $(MARKED.CDN)/$(patsubst $(CDN.JS)/marked/%,%,$@)

$(HIGHLIGHT.STUFF):
	@mkdir -p $(dir $@)
	$(WGET) --output-document=$@ $(HIGHLIGHT.CDN)/$(patsubst $(CDN.JS)/highlight/%,%,$@)

$(REVEAL.STUFF):
	@mkdir -p $(dir $@)
	$(WGET) --output-document=$@ $(REVEAL.CDN)/$(patsubst $(CDN.JS)/reveal/%,%,$@)

$(MATHJAX.STUFF):
	@mkdir -p $(dir $@)
	$(WGET) --output-document=$@ $(MATHJAX.CDN)/$(patsubst $(CDN.JS)/mathjax/%,%,$@)

# Automatic conversions

$(REP_IMAGES_AUTO)%.svg: $(REP_IMAGES_SRC)%.dia
	@mkdir -p $(dir $@)
	dia -e $@ -t svg $<

$(REP_IMAGES_AUTO)%.png: $(REP_IMAGES_SRC)%.dia
	@mkdir -p $(dir $@)
	dia -e $@ -t png $<

$(REP_IMAGES_AUTO)%.png: $(REP_IMAGES_SRC)%.svg
	@mkdir -p $(dir $@)
	inkscape --export-area-drawing --export-png $@ $<

# Actual slides and document generation

# Include MathJax in dependencies if needed...
%$(MD_SLIDEEXT): %.$(MD_BASEEXT) $(REVEAL.STUFF) $(COMDEP)
	$(PROCESSOR_DEF) --style=$(HIGHLIGHT.STYLE_S) --content2slides $< $@

%$(MD_DOCEXT): %.$(MD_BASEEXT) $(REVEAL.STUFF.FONTS) $(MARKED.STUFF) $(COMDEP)
	$(PROCESSOR_DEF) --style=$(HIGHLIGHT.STYLE_D) --content2html $< $@

# House keeping

clean:
	rm -f *$(MD_SLIDEEXT) *$(MD_DOCEXT)

distclean: clean
	rm -rf $(CDN.JS)

heavyclean: distclean
	rm -rf $(REP_IMAGES_AUTO)
