
REVEAL.JS_ZIP_URL   := https://github.com/hakimel/reveal.js/archive/master.zip
REVEAL.JS_TMP 		:= reveal-extract-tmp
REVEAL.JS_TARGET    := reveal.js

JUPYTER_NB 			:= jupyter nbconvert
JUPYTER_NB_OPTS      = --reveal-prefix=$$DEPTH/$(REVEAL.JS_TARGET)
JUPYTER_NB_SLIDESTPL = my_slides_reveal.tpl

# Not needed for now...
# JUPYTER_NB_OPTS     = 
# The command line options may differ from one nbconvert version to another...
# JUPYTER_NB_VERSION  =  $(shell $(JUPYTER_NB) --version)
# ifneq ($(filter 4.%,$(JUPYTER_NB_VERSION)), )
#   JUPYTER_NB_OPTS   = --reveal-prefix=$$DEPTH/$(REVEAL.JS_TARGET)
# endif
# ifneq ($(filter 5.%,$(JUPYTER_NB_VERSION)), )
#   JUPYTER_NB_OPTS   = --reveal-prefix=$$DEPTH/$(REVEAL.JS_TARGET)
# endif
 
IPY_NB  	= $(shell find * -name '*.ipynb')
HTML_NB		= $(patsubst %.ipynb, %.html, $(IPY_NB))
SLIDES_NB	= $(patsubst %.ipynb, %.slides.html, $(IPY_NB))

.PHONY: all slides html clean

all: slides html

slides: $(SLIDES_NB)

html: $(HTML_NB)

%.slides.html: %.ipynb $(REVEAL.JS_TARGET) $(JUPYTER_NB_SLIDESTPL)
	DEPTH=`dirname $< | perl -ne 'chomp; print join "/", (map {$$_ eq "." ? "." : ".." } split("/", $$_));'`; \
	jupyter nbconvert $< --to slides $(JUPYTER_NB_OPTS) --template $(JUPYTER_NB_SLIDESTPL)

%.html: %.ipynb
	DEPTH=`dirname $< | perl -ne 'chomp; print join "/", (map {$$_ eq "." ? "." : ".." } split("/", $$_));'`; \
	jupyter nbconvert $< --to html $(JUPYTER_NB_OPTS)

$(REVEAL.JS_TARGET):
	mkdir -p $(REVEAL.JS_TMP)
	wget --output-document=$(REVEAL.JS_TMP).zip $(REVEAL.JS_ZIP_URL)
	unzip -d $(REVEAL.JS_TMP) $(REVEAL.JS_TMP).zip
	mv $(REVEAL.JS_TMP)/* $(REVEAL.JS_TARGET)
	rm $(REVEAL.JS_TMP).zip
	rmdir $(REVEAL.JS_TMP)

clean:
	rm -rf $(REVEAL.JS_TMP)*
	rm -rf $(REVEAL.JS_TARGET)
	rm -f $(HTML_NB)
	rm -f $(SLIDES_NB)

