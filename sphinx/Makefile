# ---------------
# General options

# Path to the Python interpreter
PYTHON        = python

# Path to Vortex's doc checker
CHECKDOC      = ../project/bin/checkdoc.py
# Path to Vortex's doc generator for configuration files
GENEDOC       = ../project/bin/config2doc.py
# Path to Vortex's Notebook exporter (it converts notebooks to Rst files + attachments)
NBOOKEXPORT   = ../project/bin/notebook2sphinx.py
# Path to Footprint's collectors dumpers (generate XML/Json dumps for available resources, ...)
XMLEXPORT     = ../bin/tbinterface.py

# Path to Sphinx build program
SPHINXBUILD     = sphinx-build
# Sphinx builder command line optios
SPHINXOPTS      = 
# Preferred paper size for Sphinx +  paper size specific options
PAPER           = a4 
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter

# Build directory for the documentation
BUILDDIR      = build
# Base directory for RST files
SOURCEDIR     = .

# The final list of Sphinx options
ALLSPHINXOPTS   = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) $(SOURCEDIR)

# Target file for the documentation's checker report
CHECKREPORT   = $(SOURCEDIR)/checkreport.rst

# Target file for the geometries list
GEOLIST       = $(SOURCEDIR)/geometries.rst
# Source configuration file to generate the geometries list
GEOLIST_DEP   = ../conf/geometries.ini

# Target directory for notebook's exports
NOTEBOOKS     = notebooks
# Source directory for netbooks
NOTEBOOKS_IN  = ../examples/notebooks
# Dependencies list for the notebook generator
NOTEBOOKS_DEP = $(shell find $(NOTEBOOKS_IN) -type f -print)

# Target directory for footprint's XML exports
XMLEXPORTDIR  = $(SOURCEDIR)/_static/vortex-help/_ExportXML

# The following environment variable have to be provided in order to activate the
# automatic documentation in classes derived from FootprintBase.
FOOTPRINT_DOCSTRINGS	:= 2
export FOOTPRINT_DOCSTRINGS

# -------------
# Build targets

all: $(NOTEBOOKS) html  # HTML documentation is obviously the default

# No dependency check for the following targets (always execute them)
.PHONY: all full-check miss-check $(CHECKREPORT) html \
        clean clean-$(NOTEBOOKS) $(XMLEXPORTDIR)


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

# Do the Footprint's XML export (used in vortex-help)
$(XMLEXPORTDIR):
	mkdir -p $(XMLEXPORTDIR)
	$(PYTHON) $(XMLEXPORT) -a -f xml -o $(XMLEXPORTDIR)/tbinterface

# Build the notebooks export
$(NOTEBOOKS): $(NOTEBOOKS_DEP)
	rm -rf $(NOTEBOOKS)
	$(NBOOKEXPORT) -v -o $(NOTEBOOKS) $(NOTEBOOKS_IN)

# Build the html documentation
html: $(CHECKREPORT) $(GEOLIST) $(XMLEXPORTDIR)
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html

# Clean the notebooks
clean-$(NOTEBOOKS):
	rm -rf $(NOTEBOOKS)

# Clean the build directory and the automatically generated rst files. 
clean: clean-$(NOTEBOOKS)
	rm -rf $(BUILDDIR) $(XMLEXPORTDIR)
	rm -f $(CHECKREPORT) $(GEOLIST)
