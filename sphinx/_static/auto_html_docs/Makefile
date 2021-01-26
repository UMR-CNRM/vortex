# Were to get reveal.js
REVEAL.GIT=https://github.com/hakimel/reveal.js.git
REVEAL.JS=reveal.js

# The subdirectory that will holds pre-fetech CDN content
CDN.JS=cdn

MARKED.VERISON=0.6.3
MARKED.CDN=https://cdnjs.cloudflare.com/ajax/libs/marked/$(MARKED.VERISON)
MARKED.JS=$(CDN.JS)/marked.min.js

# If you need extra languages (e.g. fortran), this is the place !
# Note: C & Python are included by default
HIGHLIGHT.LANG=
# Code highlighting theme for slides
HIGHLIGHT.STYLE_S=sunburst
# Code highlighting theme for documents
HIGHLIGHT.STYLE_D=github

HIGHLIGHT.VERSION=9.15.10
HIGHLIGHT.CDN=https://cdnjs.cloudflare.com/ajax/libs/highlight.js/$(HIGHLIGHT.VERSION)
HIGHLIGHT.JS=$(CDN.JS)/highlight.min.js $(patsubst %, $(CDN.JS)/languages/%.min.js, $(HIGHLIGHT.LANG))
HIGHLIGHT.STYLES=$(HIGHLIGHT.STYLE_D) $(HIGHLIGHT.STYLE_S)
HIGHLIGHT.STYLES.CSS=$(patsubst %, $(CDN.JS)/highlight-%.min.css, $(HIGHLIGHT.STYLES))

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

# Common dependencies
COMDEP_IMG_AUTO=$(DIASTUFF_SVG)
#COMDEP_IMG_AUTO=$(DIASTUFF_PNG) $(SVGSTUFF_PNG)
COMDEP=$(HIGHLIGHT.STYLES.CSS) $(PROCESSOR) $(TEMPLATES) $(COMDEP_IMG_AUTO)

# Because of Meteo-France's we need this proxy :-(
ifdef VORTEX_PROJECT_SSLCERT_OVERRIDE
export GIT_SSL_CAINFO=$(VORTEX_PROJECT_SSLCERT_OVERRIDE)
WGET=wget --ca-certificate=$(VORTEX_PROJECT_SSLCERT_OVERRIDE)
else
WGET=wget
endif

.PHONY: all docs slides clean distclean $(CDN.JS)

.SECONDARY: $(HIGHLIGHT.STYLES.CSS) $(HIGHLIGHT.JS) $(MARKED.JS) $(REVEAL.JS) $(COMDEP_IMG_AUTO)

all: $(MD_SLIDE) $(MD_DOC)

docs: $(MD_DOC)

slides: $(MD_SLIDE)

# Fetch various JavaScript libraries

$(REVEAL.JS):
	git clone $(REVEAL.GIT) $@
	cd $@; git checkout master

$(MARKED.JS):
	@mkdir -p $(dir $@)
	$(WGET) --output-document=$@ $(MARKED.CDN)/$(patsubst $(CDN.JS)/%,%,$@)

$(HIGHLIGHT.JS):
	@mkdir -p $(dir $@)
	$(WGET) --output-document=$@ $(HIGHLIGHT.CDN)/$(patsubst $(CDN.JS)/%,%,$@)

$(CDN.JS)/highlight-%.min.css:
	@mkdir -p $(dir $@)
	$(WGET) --output-document=$@ $(HIGHLIGHT.CDN)/styles/$*.min.css

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

%$(MD_SLIDEEXT): %.$(MD_BASEEXT) $(REVEAL.JS) $(COMDEP)
	$(PROCESSOR_DEF) --style=$(HIGHLIGHT.STYLE_S) --content2slides $< $@

%$(MD_DOCEXT): %.$(MD_BASEEXT) $(REVEAL.JS) $(MARKED.JS) $(HIGHLIGHT.JS) $(COMDEP)
	$(PROCESSOR_DEF) --style=$(HIGHLIGHT.STYLE_D) --content2html $< $@

# House keeping

clean:
	rm -f *$(MD_SLIDEEXT) *$(MD_DOCEXT)

distclean: clean
	rm -rf $(REVEAL.JS) $(CDN.JS)

heavyclean: dsitclean
	rm -rf $(REP_IMAGES_AUTO)
