# ---------------
# General options

# Path to the Python interpreter
PYTHON        = python3

# Path to Vortex's doc checker
CHECKDOC      = ../project/bin/checkdoc.py
# Path to Vortex's index generator
GENEINDEX     = ../project/bin/package_doc_index.py
# Path to Vortex's doc generator for configuration files
GENEDOC       = ../project/bin/config2doc.py
# Path to Vortex's Notebook exporter (it converts notebooks to Rst files + attachments)
NBOOKEXPORT   = ../project/bin/notebook2sphinx.py

# Path to Sphinx build program
SPHINXBUILD     = sphinx-build
# Sphinx builder command line optios
SPHINXOPTS      =

# Build directory for the documentation
BUILDDIR      = build
# Base directory for RST files
SOURCEDIR     = .

# The final list of Sphinx options
ALLSPHINXOPTS   = $(SPHINXOPTS) $(SOURCEDIR)

# Target file for the documentation's checker report
CHECKREPORT   = $(SOURCEDIR)/checkreport.rst

# Target file for the geometries list
GEOLIST       = $(SOURCEDIR)/geometries.rst
# Source configuration file to generate the geometries list
GEOLIST_DEP   = ../conf/geometries.ini

# Target file for the BDPE ids list
BDPELIST       = $(SOURCEDIR)/bdpe-map-resources.rst
# Source configuration file to generate the BDPE ids list
BDPELIST_DEP   = ../conf/bdpe-map-resources.ini

# Target file for the pollutants list
POL_ELTS      = $(SOURCEDIR)/pollutants-elements-std.rst
POL_SITES     = $(SOURCEDIR)/pollutants-sites-std.rst
# Source configuration file to generate the pollutants list
POL_ELTS_DEP   = ../conf/pollutants-elements-std.ini
POL_SITES_DEP  = ../conf/pollutants-sites-std.ini

# Target directory for notebook's exports
NOTEBOOKS     = notebooks
# Source directory for netbooks
NOTEBOOKS_IN  = ../examples/notebooks
# Dependencies list for the notebook generator
NOTEBOOKS_DEP = $(shell find $(NOTEBOOKS_IN) -type f -print)

# Librarie indexes to be built...
AUTO_LIBINDEXES = $(shell find library/* -maxdepth 0 -type d -print)
BUILD_LIBINDEXES = $(patsubst library/%, %_libindex, $(AUTO_LIBINDEXES))
CLEAN_LIBINDEXES = $(patsubst library/%, clean-%_libindex, $(AUTO_LIBINDEXES))

# Auto html doc
AUTO_HTML_DOC = _static/auto_html_docs

# The following environment variable have to be provided in order to activate the
# automatic documentation in classes derived from FootprintBase.
FOOTPRINT_DOCSTRINGS	:= 2
export FOOTPRINT_DOCSTRINGS


# -------------
# Build targets

VORTEXBASE  := $(shell pwd)/..
EXTRAPATH   := $(VORTEXBASE)/src:$(VORTEXBASE)/site:$(VORTEXBASE)/project:$(VORTEXBASE)/tests:$(PYTHONPATH)
export PYTHONPATH = $(EXTRAPATH)


all: auto_html_docs html  # HTML documentation is obviously the default

# No dependency check for the following targets (always execute them)
.PHONY: all full-check miss-check $(CHECKREPORT) html auto_html_docs \
        clean clean-$(NOTEBOOKS) clean-auto_html_docs

# Create rst files for new modules and check all of the aspects
full-check:
	$(PYTHON) $(CHECKDOC)

# Create rst files for new modules and check only for missing objects in rst
# files
miss-check:
	$(PYTHON) $(CHECKDOC) --light

# Generate the checkdoc report (that will be included in the doc)
$(CHECKREPORT):
	$(PYTHON) $(CHECKDOC) --gen-report=$@

# Other automatic lists
# Geometries:
$(GEOLIST): $(GEOLIST_DEP)
	$(PYTHON) $(GENEDOC) --geometry $(GEOLIST)

$(BDPELIST): $(BDPELIST_DEP)
	$(PYTHON) $(GENEDOC) --default $(BDPELIST_DEP) $(BDPELIST)

$(POL_ELTS): $(POL_ELTS_DEP)
	$(PYTHON) $(GENEDOC) --configtable pollutants,elements,std,en,intairpol $(POL_ELTS)

$(POL_SITES): $(POL_SITES_DEP)
	$(PYTHON) $(GENEDOC) --configtable pollutants,sites,std,en,intairpol $(POL_SITES)

# Build the notebooks export
$(NOTEBOOKS): $(NOTEBOOKS_DEP)
	rm -rf $(NOTEBOOKS)
	$(PYTHON) $(NBOOKEXPORT) -v -o $(NOTEBOOKS) $(NOTEBOOKS_IN)

# Clean a library index
clean-%_libindex:
	$(PYTHON) $(GENEINDEX) -v --clean $(patsubst clean-%_libindex, library/%, $@)

# Standard build for library indexes
%_libindex:
	$(PYTHON) $(GENEINDEX) -v $(patsubst %_libindex, library/%, $@)

# Special builds for some library indexes (custom versionid)
taylorism_libindex:
	$(PYTHON) $(GENEINDEX) -v --versionid version_taylorism $(patsubst %_libindex, library/%, $@)

footprints_libindex:
	$(PYTHON) $(GENEINDEX) -v --versionid version_fp $(patsubst %_libindex, library/%, $@)

# Build the $(AUTO_HTML_DOC) directory
auto_html_docs:
	make -C $(AUTO_HTML_DOC) docs

# Build the sphinx-html documentation
html: $(NOTEBOOKS) $(CHECKREPORT) $(GEOLIST) $(BDPELIST) $(POL_ELTS) $(POL_SITES) $(BUILD_LIBINDEXES)
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html

# Clean the notebooks
clean-$(NOTEBOOKS):
	rm -rf $(NOTEBOOKS)

clean-auto_html_docs:
	make -C $(AUTO_HTML_DOC) distclean

# Clean the build directory and the automatically generated rst files.
clean: clean-$(NOTEBOOKS) clean-auto_html_docs $(CLEAN_LIBINDEXES)
	rm -rf $(BUILDDIR)
	rm -f $(CHECKREPORT) $(GEOLIST) $(BDPELIST) $(POL_ELTS) $(POL_SITES)
