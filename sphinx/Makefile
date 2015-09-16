# General options
PYTHON        = python

SPHINXBUILD   = sphinx-build
CHECKDOC      = ../bin/checkdoc.py

SPHINXOPTS    =
PAPER         = a4
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter

BUILDDIR      = build
SOURCEDIR     = ./

ALLSPHINXOPTS   = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) $(SOURCEDIR)


# To enable footprint to generate its documentation
FOOTPRINT_DOCSTRINGS	:= 1
export FOOTPRINT_DOCSTRINGS


all: html


# Create rst files for new modules and check all of the aspects
full-check:
	$(PYTHON) $(CHECKDOC)

# Create rst files for new modules and check only for missing objects in rst
# files
miss-check:
	$(PYTHON) $(CHECKDOC) missingonly=on

# Generate the checkdoc report
checkreport:
	$(PYTHON) $(CHECKDOC) generaterst=$(SOURCEDIR)/checkreport.rst

# Build the html documentation
html: checkreport
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html

# Clean the build directory and checkdoc report
clean:
	rm -rf $(BUILDDIR)
	rm -f $(SOURCEDIR)/checkreport.rst

