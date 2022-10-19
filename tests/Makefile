
VORTEXBASE  := $(shell pwd)/..
EXTRAPATH   := $(VORTEXBASE)/src:$(VORTEXBASE)/site:$(VORTEXBASE)/project:$(VORTEXBASE)/tests:$(PYTHONPATH)
export PYTHONPATH = $(EXTRAPATH)

PYTHON        = python2.7
NOSE          = nosetests-2.7

PYTHON3       = python3
PYTEST        = pytest

NOSE_OPTS     = --verbosity=2 --no-byte-compile
PYTEST_OPTS   =

COVER_PACK    = footprints,bronx,tnt,taylorism,arpifs_listings,vortex,common,olive,gco,iga,alpha,cen,davai,ecmwf,intairpol,previmar,promethee
COVER_OUT	  = coverage_report

comma:= ,
empty:=
space:= $(empty) $(empty)

N_COVER_OPTS  = --no-byte-compile --with-coverage --cover-package=$(COVER_PACK) --cover-branch --cover-html --cover-html-dir=$(shell pwd)/$(COVER_OUT)
P_COVER_OPTS  = $(foreach p,$(subst $(comma),$(space),$(COVER_PACK)),--cov=$p) --cov-report html:$(COVER_OUT)
all: check

.PHONY: all check check27 check3 tests tests27 tests3 baretests baretests27 baretests3 cover cover27 cover3 clean-coverage clean


# Tests that should always succeed and are fast enough
check: check3

check27:
	$(PYTHON) ./do_working_tests-2.7.py

check3:
	$(PYTHON3) ./do_working_tests-3.py

# Run all test with nose
tests: tests3

tests27:
	($(NOSE) $(NOSE_OPTS) 2>&1) | tee $@.log

tests3:
	($(PYTEST) $(PYTESTS_OPTS) 2>&1) | tee $@.log

# Run all test without nose
baretests: baretests3

baretests27:
	$(PYTHON) ./do_all_tests.py

baretests3:
	$(PYTHON3) ./do_all_tests.py

# Run all tests with nose and coverage
cover: cover3

cover27: clean-coverage
	export VORTEX_TEST_NAMES_NTASKS=1; $(NOSE) $(N_COVER_OPTS)

cover3: clean-coverage
	export VORTEX_TEST_NAMES_NTASKS=1; $(PYTEST) $(P_COVER_OPTS)

clean-coverage:
	rm -f .coverage
	rm -rf $(COVER_OUT)

# Clean the test directories
clean: clean-coverage
	@# nothing else at the moment

