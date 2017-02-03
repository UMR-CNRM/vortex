PYTHON        = python
NOSE          = nosetests

NOSE_OPTS     = --verbosity=2 --no-byte-compile

COVER_PACK    = footprints,vortex,common,olive,gco,iga,taylorism,arpifs_listings
COVER_OUT	  = coverage_report
COVER_OPTS    = --no-byte-compile --with-coverage --cover-package=$(COVER_PACK) --cover-branch --cover-html --cover-html-dir=$(shell pwd)/$(COVER_OUT)

all: check

.PHONY: all check tests cover clean-coverage clean


# Tests that should always succeed
check:
	$(PYTHON) ./do_working_tests.py

# Run all test with nose
tests:
	$(NOSE) $(NOSE_OPTS)

# Run all tests with nose and coverage
cover: clean-coverage
	$(NOSE) $(COVER_OPTS)

clean-coverage:
	rm -f .coverage
	rm -rf $(COVER_OUT)

# Clean the test directories (nothing to be done at the moment)
clean: clean-coverage

