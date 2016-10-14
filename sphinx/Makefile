# General options
PYTHON        = python

SPHINXBUILD   = sphinx-build
CHECKDOC      = ../project/bin/checkdoc.py
GENEDOC       = ../project/bin/config2doc.py
NBOOKEXPORT   = ../project/bin/notebook2sphinx.py
XMLEXPORT     = ../bin/tbinterface.py

SPHINXOPTS    =
PAPER         = a4
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter

BUILDDIR      = build
SOURCEDIR     = .
CHECKREPORT   = $(SOURCEDIR)/checkreport.rst
GEOLIST       = $(SOURCEDIR)/geometries.rst
GEOLIST_DEP   = ../conf/geometries.ini
NOTEBOOKS     = notebooks
NOTEBOOKS_IN  = ../examples/notebooks
NOTEBOOKS_DEP = $(shell find $(NOTEBOOKS_IN) -name *.ipynb -print) $(shell find $(NOTEBOOKS_IN) -type d -print)
XMLEXPORTDIR  = $(SOURCEDIR)/_static/vortex-help/_ExportXML

ALLSPHINXOPTS   = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) $(SOURCEDIR)


# To enable footprint to generate its documentation
FOOTPRINT_DOCSTRINGS	:= 2
export FOOTPRINT_DOCSTRINGS


all: html

.PHONY: all full-check miss-check $(CHECKREPORT) html clean clean-$(NOTEBOOKS) $(XMLEXPORTDIR)


# Create rst files for new modules and check all of the aspects
full-check:
	$(PYTHON) $(CHECKDOC)

# Create rst files for new modules and check only for missing objects in rst
# files
miss-check:
	$(PYTHON) $(CHECKDOC) missingonly=on

# Generate the checkdoc report
$(CHECKREPORT):
	$(PYTHON) $(CHECKDOC) generaterst=$@

# Other automatic lists
$(GEOLIST): $(GEOLIST_DEP)
	$(PYTHON) $(GENEDOC) --geometry $(GEOLIST)

# Build the notebooks export
$(NOTEBOOKS): $(NOTEBOOKS_DEP)
	rm -rf $(NOTEBOOKS)
	$(NBOOKEXPORT) -v -o $(NOTEBOOKS) $(NOTEBOOKS_IN)

# Do the XML exort
$(XMLEXPORTDIR):
	mkdir -p $(XMLEXPORTDIR)
	$(PYTHON) $(XMLEXPORT) -a -f xml -o $(XMLEXPORTDIR)/tbinterface

# Build the html documentation
html: $(CHECKREPORT) $(GEOLIST) $(NOTEBOOKS) $(XMLEXPORTDIR)
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html

clean-$(NOTEBOOKS):
	rm -rf $(NOTEBOOKS)

# Clean the build directory and the checkdoc report
clean: clean-$(NOTEBOOKS)
	rm -rf $(BUILDDIR) $(XMLEXPORTDIR)
	rm -f $(CHECKREPORT) $(GEOLIST)

