CLOCPY		= project/bin/countlines.py
CLOCDEF		= project/cloc.defs
CLOCBIN     = cloc

DOC_DIR		= sphinx
TEST_DIR	= tests

STYLEPY		= project/bin/vortex_codechecker.py

SUBDIRS		= tests sphinx
CLEANDIRS 	= $(SUBDIRS:%=clean-%)

VORTEXBASE  := $(shell pwd)
EXTRAPATH   := $(VORTEXBASE)/src:$(VORTEXBASE)/site:$(VORTEXBASE)/project:$(VORTEXBASE)/tests:$(PYTHONPATH)
export PYTHONPATH = $(EXTRAPATH)


.PHONY: check tests cover doc style cloc cloc_all pylint flake8 clean $(CLEANDIRS)

# Run a minimal set of tests (should always succeed)
check:
	$(MAKE) -C $(TEST_DIR)

# Run all the test suite using nose
tests:
	$(MAKE) -C $(TEST_DIR) tests

# Run the unittest's code coverage analysis
cover:
	$(MAKE) -C $(TEST_DIR) cover

# Build the sphinx documentation
doc:
	$(MAKE) -C $(DOC_DIR)

# Run the Vortex's code chercker
style:
	$(STYLEPY)

# Count the number of source code lines
cloc        : ; $(CLOCPY) -p $(CLOCBIN) -d $(CLOCDEF) site src tests conf,templates examples sphinx
cloc_all    : ; $(CLOCPY) -p $(CLOCBIN) -d $(CLOCDEF) .

# Code quality analysis : pyflakes + pep8 + McCabe (cyclomatic complexity)
flake8: ; flake8 --config=project/flake8.ini --statistics . > project/flake8_report.txt || true

# Code quality analysis : pylint
pylint:
	bin/tbinterface.py -a -c all -n 'cen,common,ecmwf,gco,iga,intairpol,olive,previmar,sandbox' -f json -o 'project/tbinterface'
	pylint --rcfile=project/pylint.rc src/* site/* > project/pylint_global.txt || true


# List of git contributors (for icons in project/gource_users/)
contributors:
	@find src site -type f -name "*.py" \
	| while read f ; do git blame -p $$f ; done \
	| sed -n 's/^author //p' \
	| sort \
	| uniq -c \
	| sort -nr

# View the animated history of the project's contributions
gource:
	gource -i 0 -s 0.1 --bloom-multiplier 0.7 -c 0.8 -f \
	       --user-image-dir project/gource_users

# Clean all the directories, then locally
clean: $(CLEANDIRS)
	rm -f project/{flake8_report,pylint_global}.txt
	rm -f project/tbinterface_*.json
	rm -rf .pytest_cache
	find . -name "*.pyc"       -print0 | xargs -0r rm
	find . -name "__pycache__" -print0 | xargs -0r rm -r

$(CLEANDIRS):
	$(MAKE) -C $(@:clean-%=%) clean

# Usual target
clobber: clean
