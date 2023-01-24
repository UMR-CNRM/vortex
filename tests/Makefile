
VORTEXBASE  := $(shell pwd)/..
EXTRAPATH   := $(VORTEXBASE)/src:$(VORTEXBASE)/site:$(VORTEXBASE)/project:$(VORTEXBASE)/tests:$(PYTHONPATH)
export PYTHONPATH = $(EXTRAPATH)

PYTHON3       = python3
PYTEST        = pytest

PYTEST_OPTS   =

COVER_PACK    = footprints,bronx,tnt,taylorism,arpifs_listings,vortex,common,olive,gco,iga,alpha,cen,davai,ecmwf,intairpol,previmar,promethee
COVER_OUT	  = coverage_report

comma:= ,
empty:=
space:= $(empty) $(empty)

P_COVER_OPTS  = $(foreach p,$(subst $(comma),$(space),$(COVER_PACK)),--cov=$p) --cov-report html:$(COVER_OUT)
all: check

.PHONY: all check check3 tests tests3 baretests baretests3 cover cover3 clean-coverage clean


# Tests that should always succeed and are fast enough
check: check3

check3:
	$(PYTHON3) ./do_working_tests-3.py

# Run all test with nose
tests: tests3

tests3:
	($(PYTEST) $(PYTESTS_OPTS) 2>&1) | tee $@.log

# Run all test without nose
baretests: baretests3

baretests3:
	$(PYTHON3) ./do_all_tests.py

# Run all tests with nose and coverage
cover: cover3

cover3: clean-coverage
	export VORTEX_TEST_NAMES_NTASKS=1; $(PYTEST) $(P_COVER_OPTS)

clean-coverage:
	rm -f .coverage
	rm -rf $(COVER_OUT)

# Clean the test directories
clean: clean-coverage
	@# nothing else at the moment
