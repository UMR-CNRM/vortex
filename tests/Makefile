
EXTRAPATH    := $(PWD)/../src:$(PWD)/../site:$(PWD)/../project:$(PYTHONPATH)
export PYTHONPATH = $(EXTRAPATH)

PYTHON        = python2.7
NOSE          = nosetests-2.7

PYTHON3       = python3
NOSE3list     = nosetests-3.5 nosetests-3.4 nosetests3
NOSE3         = $(shell for p in $(NOSE3list) ; do if which $$p >/dev/null 2>&1 ; then echo $$p ; break ; fi ; done)

NOSE_OPTS     = --verbosity=2 --no-byte-compile

COVER_PACK    = footprints,vortex,common,olive,gco,iga,taylorism,arpifs_listings,bronx,tnt
COVER_OUT	  = coverage_report
COVER_OPTS    = --no-byte-compile --with-coverage --cover-package=$(COVER_PACK) --cover-branch --cover-html --cover-html-dir=$(shell pwd)/$(COVER_OUT)

PY3READY      = tests_bronx tests_footprints tests_arpifs_listings tests_tnt test_taylorism

all: check

.PHONY: all check tests cover clean-coverage clean


# Tests that should always succeed
check:
	$(PYTHON) ./do_working_tests.py

check3:
	$(PYTHON3) ./do_working_tests-3.py

# Run all test with nose
tests:
	$(NOSE3) $(NOSE_OPTS) $(PY3READY)
	$(NOSE) $(NOSE_OPTS)

# Run all tests with nose and coverage
cover: clean-coverage
	$(NOSE) $(COVER_OPTS)

clean-coverage:
	rm -f .coverage
	rm -rf $(COVER_OUT)

# Clean the test directories
clean: clean-coverage
	@# nothing else at the moment

